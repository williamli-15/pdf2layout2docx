# -*- coding: utf-8 -*-

'''A wrapper of pdf page engine (e.g. PyMuPDF, pdfminer) to do the following work:

* extract source contents
* clean up blocks/shapes, e.g. elements out of page
* calculate page margin
* parse page structure roughly, i.e. section and column
'''

from .BasePage import BasePage
from ..layout.Layout import Layout
from ..layout.Section import Section
from ..layout.Column import Column
from ..shape.Shape import Hyperlink
from ..shape.Shapes import Shapes
from ..font.Fonts import Fonts
from ..text.TextSpan import TextSpan
from ..common.share import debug_plot
from ..common import constants
from ..common.Collection import Collection
import numpy as np
import pdb


class RawPage(BasePage, Layout):
    '''A wrapper of page engine.'''

    def __init__(self, page_engine=None):
        ''' Initialize page layout.
        
        Args:
            page_engine (Object): Source pdf page.
        '''
        BasePage.__init__(self)
        Layout.__init__(self)
        self.page_engine = page_engine
    

    def extract_raw_dict(self, **settings):
        '''Extract source data with page engine. Return a dict with the following structure:
        ```
            {
                "width" : w,
                "height": h,    
                "blocks": [{...}, {...}, ...],
                "shapes" : [{...}, {...}, ...]
            }
        ```
        '''
        raise NotImplementedError
    
    @property
    def text(self):
        '''All extracted text in this page, with images considered as ``<image>``. 
        Should be run after ``restore()`` data.'''
        return '\n'.join([block.text for block in self.blocks])

    @property
    def raw_text(self):
        '''Extracted raw text in current page. Should be run after ``restore()`` data.'''
        return '\n'.join([block.raw_text for block in self.blocks])


    @debug_plot('Source Text Blocks')
    def restore(self, **settings):
        '''Initialize layout extracted with ``PyMuPDF``.'''
        raw_dict = self.extract_raw_dict(**settings)
        super().restore(raw_dict)    ###对block和shape进行解释
        return self.blocks

    @debug_plot('Source Text Blocks image')
    def restore_image(self,raw_dict, **settings):
        '''Initialize layout extracted with ``PyMuPDF``.'''
        raw_dict = self.extract_raw_dict_img(raw_dict,**settings)
        super().restore(raw_dict)    ###对block和shape进行解释
        return self.blocks

    
    @debug_plot('Cleaned Shapes')
    def clean_up(self, **settings):
        '''Clean up raw blocks and shapes, e.g. 
        
        * remove negative or duplicated instances,
        * detect semantic type of shapes
        '''
        # clean up blocks first
        self.blocks.clean_up(
            settings['float_image_ignorable_gap'],
            settings['line_overlap_threshold'])

        # clean up shapes        
        self.shapes.clean_up(
            settings['max_border_width'],
            settings['shape_min_dimension'])
        
        return self.shapes

    @debug_plot('Cleaned table Shapes')
    def clean_up_table(self, **settings):
        '''Clean up raw blocks and shapes, e.g.

        * remove negative or duplicated instances,
        * detect semantic type of shapes
        '''
        table_blocks_array = self.blocks.table_blocks

        # # clean up blocks first
        # self.blocks.clean_up(
        #     settings['float_image_ignorable_gap'],
        #     settings['line_overlap_threshold'])

        for table_block in self.blocks.table_blocks:

            for Row in table_block._rows._instances:
                for Cell in Row._cells._instances:

                     blocks=Cell.blocks
                     blocks.clean_up(settings['float_image_ignorable_gap'],settings['line_overlap_threshold'])

        return self


    def process_font(self, fonts:Fonts):      
        '''Update font properties, e.g. font name, font line height ratio, of ``TextSpan``.
        
        Args:
            fonts (Fonts): Fonts parsed by ``fonttools``.
        '''
        # get all text span
        spans = []
        for line in self.blocks:
            spans.extend([span for span in line.spans if isinstance(span, TextSpan)])

        # check and update font name, line height
        for span in spans:
            font = fonts.get(span.font)
            if not font: continue

            # update font properties with font parsed by fonttools
            span.font = font.name
            if font.line_height:
                span.line_height = font.line_height * span.size


    def calculate_margin(self, **settings):
        """Calculate page margin.

        .. note::
            Ensure this method is run right after cleaning up the layout, so the page margin is 
            calculated based on valid layout, and stay constant.
        """
        # Exclude hyperlink from shapes because hyperlink might exist out of page unreasonablely, 
        # while it should always within page since attached to text.
        shapes = Shapes([shape for shape in self.shapes if not isinstance(shape, Hyperlink)])

        # return default margin if no blocks exist
        if not self.blocks and not shapes: return (constants.ITP, ) * 4

        x0, y0, x1, y1 = self.bbox
        u0, v0, u1, v1 = self.blocks.bbox | shapes.bbox

        # margin
        left = max(u0-x0, 0.0)
        right = max(x1-u1-constants.MINOR_DIST, 0.0)
        top = max(v0-y0, 0.0)
        bottom = max(y1-v1, 0.0)

        # reduce calculated top/bottom margin to leave some free space
        top *= settings['page_margin_factor_top']
        bottom *= settings['page_margin_factor_bottom']

        # use normal margin if calculated margin is large enough
        return (
            min(constants.ITP, round(left, 1)), 
            min(constants.ITP, round(right, 1)), 
            min(constants.ITP, round(top, 1)), 
            min(constants.ITP, round(bottom, 1)))


    def parse_section(self, **settings):
        '''Detect and create page sections.

        .. note::
            - Only two-columns Sections are considered for now.
            - Page margin must be parsed before this step.
        '''
        # bbox
        X0, Y0, X1, _ = self.working_bbox
    
        # collect all blocks (line level) and shapes
        elements = Collection()
        elements.extend(self.blocks)
        elements.extend(self.shapes)
        if not elements: return

        # to create section with collected lines        
        lines = Collection()        
        sections = []
        def close_section(num_col, elements, y_ref):
            # append to last section if both single column
            if sections and sections[-1].num_cols==num_col==1:
                column = sections[-1][0] # type: Column
                column.union_bbox(elements)
                column.add_elements(elements)
            # otherwise, create new section
            else:
                section = self._create_section(num_col, elements, (X0, X1), y_ref)
                if section: 
                    sections.append(section)


        # check section row by row
        pre_num_col = 1
        y_ref = Y0 # to calculate v-distance between sections
        for row in elements.group_by_rows():
            # check column col by col
            cols = row.group_by_columns()
            current_num_col = len(cols)

            # column check:
            # consider 2-cols only
            if current_num_col>2:
                current_num_col = 1
            
            # the width of two columns shouldn't have significant difference
            elif current_num_col==2:
                u0, v0, u1, v1 = cols[0].bbox
                m0, n0, m1, n1 = cols[1].bbox
                x0 = (u1+m0)/2.0
                c1, c2 = x0-X0, X1-x0 # column width
                w1, w2 = u1-u0, m1-m0 # line width
                f = 2.0
                if not 1/f<=c1/c2<=f or w1/c1<0.33 or w2/c2<0.33: 
                    current_num_col = 1

            # process exceptions
            if pre_num_col==2 and current_num_col==1:
                # though current row has one single column, it might have another virtual 
                # and empty column. If so, it should be counted as 2-cols
                cols = lines.group_by_columns()
                pos = cols[0].bbox[2]
                if row.bbox[2]<=pos or row.bbox[0]>pos:
                    current_num_col = 2
                
                # pre_num_col!=current_num_col => to close section with collected lines,
                # before that, further check the height of collected lines
                else:
                    x0, y0, x1, y1 = lines.bbox
                    if y1-y0<settings['min_section_height']:
                        pre_num_col = 1
                

            elif pre_num_col==2 and current_num_col==2:
                # though both 2-cols, they don't align with each other
                combine = Collection(lines)
                combine.extend(row)
                if len(combine.group_by_columns(sorted=False))==1: current_num_col = 1


            # finalize pre-section if different from the column count of previous section
            if current_num_col!=pre_num_col:
                # process pre-section
                close_section(pre_num_col, lines, y_ref)
                if sections: 
                    y_ref = sections[-1][-1].bbox[3]

                # start potential new section                
                lines = Collection(row)
                pre_num_col = current_num_col

            # otherwise, collect current lines for further processing
            else:
                lines.extend(row)

        # don't forget the final section
        close_section(current_num_col, lines, y_ref)

        return sections

    def parse_section_DoubleLayout(self,sections_count_list,columns_count_list, **settings):
        '''Detect and create page sections.

        .. note::
            - Only two-columns Sections are considered for now.
            - Page margin must be parsed before this step.
        '''
        # bbox
        X0, Y0, X1, _ = self.working_bbox

        # collect all blocks (line level) and shapes  所有的文本行
        elements = Collection()
        elements.extend(self.blocks)
        elements.extend(self.shapes)
        if not elements: return

        ####To Do
        #########如果不对齐，调取原来的输出
        if(len(elements._instances)!=len(sections_count_list)):
            sections=self.parse_section( **settings)
            return sections
            # ##找出elements中对应的idx不对齐的结果
            # init_blocks=self.blocks._instances
            # for line_idx,line in enumerate(init_blocks):
            #     if(int(sum(line.bbox))==0):
            #         columns_count_list.pop(line_idx)
            #         sections_count_list.pop(line_idx)


        # to create section with collected lines
        lines = Collection()
        sections = []

        def close_section(num_col, elements, y_ref,cols):
            # append to last section if both single column
            if sections and sections[-1].num_cols == num_col == 1:
                column = sections[-1][0]  # type: Column
                column.union_bbox(elements)
                column.add_elements(elements)
            # otherwise, create new section
            else:
                section = self._create_section(num_col, elements, (X0, X1), y_ref,cols)
                if section:
                    sections.append(section)


        # check section row by row
        pre_num_col = 1
        y_ref = Y0 # to calculate v-distance between sections

        ###按行简单切分多个sections，依据每个section再按columns排序
        section_rows_groups=[]
        section_total_num=max(sections_count_list)+1
        sections_count_list=np.array(sections_count_list)

        for sec_num in range(section_total_num):
            idxs=np.where(sections_count_list==sec_num)[0]
            counted_indexes = set()
            for id in idxs:
                counted_indexes.add(id)
            section_rows_groups.append(counted_indexes)

        section_rows = [elements.__class__([elements._instances[i] for i in group]) for group in section_rows_groups]

        init_rows_count=0
        for row_idx,row in enumerate(section_rows):
            #*************按列分组***********************
            row_line_num=len(row._instances)

            current_column_classify=columns_count_list[init_rows_count:init_rows_count+row_line_num]
            init_rows_count=init_rows_count+row_line_num               ####计算到原始对应的当前行数


            if(sum(current_column_classify)==0):   ###证明只有单列
                column_groups = []
                counted_indexes = set()
                for id in range(row_line_num):
                    counted_indexes.add(id)
                column_groups.append(counted_indexes)
                cols = [row.__class__([row._instances[i] for i in group]) for group in column_groups]

            else:
                right_num=sum(current_column_classify)
                column_groups=[]

                counted_indexes = set()
                for id in range(row_line_num-right_num):
                    counted_indexes.add(id)

                column_groups.append(counted_indexes)

                counted_indexes = set()
                for id in range(row_line_num-right_num,row_line_num):
                    counted_indexes.add(id)

                column_groups.append(counted_indexes)

                cols = [row.__class__([row._instances[i] for i in group]) for group in
                        column_groups]

            current_num_col = len(cols)

            lines = Collection(row)
            close_section(current_num_col, lines, y_ref,cols)
            if sections:
                y_ref = sections[-1][-1].bbox[3]

            # ************************************#

        # ************initial version***************************************************#
        #     cols = row.group_by_columns()
        #
        #     current_num_col = len(cols)
        #     # column check:
        #     # consider 2-cols only
        #     if current_num_col > 2:
        #         current_num_col = 1
        #
        #     # the width of two columns shouldn't have significant difference
        #     elif current_num_col == 2:
        #         u0, v0, u1, v1 = cols[0].bbox
        #         m0, n0, m1, n1 = cols[1].bbox
        #         x0 = (u1 + m0) / 2.0
        #         c1, c2 = x0 - X0, X1 - x0  # column width
        #         w1, w2 = u1 - u0, m1 - m0  # line width
        #         f = 2.0
        #         if not 1 / f <= c1 / c2 <= f or w1 / c1 < 0.33 or w2 / c2 < 0.33:
        #             current_num_col = 1
        #
        #     # process exceptions
        #     if pre_num_col==2 and current_num_col==1:       ##双面，有一面为空
        #         # though current row has one single column, it might have another virtual
        #         # and empty column. If so, it should be counted as 2-cols
        #         cols = lines.group_by_columns()
        #         pos = cols[0].bbox[2]
        #         if row.bbox[2]<=pos or row.bbox[0]>pos:
        #             current_num_col = 2
        #
        #         # pre_num_col!=current_num_col => to close section with collected lines,
        #         # before that, further check the height of collected lines
        #         else:
        #             x0, y0, x1, y1 = lines.bbox
        #             if y1-y0<settings['min_section_height']:
        #                 pre_num_col = 1
        #
        #     elif pre_num_col==2 and current_num_col==2:                   ##虽然两列，但是并不对齐
        #         # though both 2-cols, they don't align with each other
        #         combine = Collection(lines)
        #         combine.extend(row)
        #         if len(combine.group_by_columns(sorted=False))==1: current_num_col = 1
        #
        #     # finalize pre-section if different from the column count of previous section
        #     # 如果与上一个section的列数不同，则创建一个新的section
        #     if current_num_col!=pre_num_col:
        #         # process pre-section
        #         close_section(pre_num_col, lines, y_ref)
        #         if sections:
        #             y_ref = sections[-1][-1].bbox[3]
        #
        #         # start potential new section
        #         lines = Collection(row)
        #         pre_num_col = current_num_col
        #
        #     # otherwise, collect current lines for further processing
        #     else:
        #         lines.extend(row)
        #
        #
        # # don't forget the final section
        # current_num_col=1
        # close_section(current_num_col, lines, y_ref)     ##单面的只走这一步

        ####update by chen##############################
        #########Split line#####################

        return sections


    @staticmethod
    def _create_section(num_col:int, elements:Collection, h_range:tuple, y_ref:float,cols=None):
        '''Create section based on column count, candidate elements and horizontal boundary.'''
        if not elements: return
        X0, X1 = h_range

        if num_col==1:
            x0, y0, x1, y1 = elements.bbox
            column = Column().update_bbox((X0, y0, X1, y1))
            column.add_elements(elements)
            section = Section(space=0, columns=[column])
            before_space = y0 - y_ref
        else:
            if(cols==None):
                cols = elements.group_by_columns()
            u0, v0, u1, v1 = cols[0].bbox
            m0, n0, m1, n1 = cols[1].bbox
            u = (u1+m0)/2.0

            column_1 = Column().update_bbox((X0, v0, u, v1))
            column_1.add_elements(elements)

            column_2 = Column().update_bbox((u, n0, X1, n1))
            column_2.add_elements(elements)

            section = Section(space=0, columns=[column_1, column_2])
            before_space = v0 - y_ref

        section.before_space = round(before_space, 1)
        return section


    def bb_intersection_over_union(self, boxA, boxB):
        boxA = [int(x) for x in boxA]
        boxB = [int(x) for x in boxB]

        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        interArea = max(0, xB - xA + 1) * max(0, yB - yA + 1)

        boxAArea = (boxA[2] - boxA[0] + 1) * (boxA[3] - boxA[1] + 1)
        boxBArea = (boxB[2] - boxB[0] + 1) * (boxB[3] - boxB[1] + 1)

        iou = interArea / float(boxAArea + boxBArea - interArea)
        return iou

    def parse_section_Table_sort(self, table_blocks_array,sections, **settings):

        print('sections: {}'.format(sections))

        if sections == None:
            return sections
        for section_id,section in enumerate(sections):
            sec_bbox=section.bbox

            for table_block in table_blocks_array:
                table_bbox=table_block.bbox

                iou_ration = self.bb_intersection_over_union(sec_bbox, table_bbox)

                ##table在当前section中
                if (iou_ration > 0.05):

                    blocks=[]
                    shapes=[]
                    for col_id,column in enumerate(section._instances):
                        col_bbox=column.bbox
                        column_iou_ration = self.bb_intersection_over_union(col_bbox, table_bbox)

                        if (column_iou_ration > 0.05):
                            # column.blocks.assign_to_tables(table_block)
                            # self.sections[section_id]._instances[col_id].blocks.assign_to_tables(table_block)
                            # self.sections[section_id].reset(self.sections[section_id]._instances[col_id])

                            A=column.blocks
                            B=column.shapes

                            # column.blocks._instances.append(table_block)
                            sections[section_id]._instances[col_id].blocks._instances.append(table_block)


        return sections
