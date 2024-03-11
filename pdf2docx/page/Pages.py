# -*- coding: utf-8 -*-

'''Collection of :py:class:`~pdf2docx.page.Page` instances.'''

import logging

from .RawPageFactory import RawPageFactory
from ..common.Collection import BaseCollection
from ..font.Fonts import Fonts
import numpy as np
import pdb
import json

class Pages(BaseCollection):
    '''A collection of ``Page``.'''

    def parse(self, fitz_doc, **settings):
        '''Analyse document structure, e.g. page section, header, footer.

        Args:
            fitz_doc (fitz.Document): ``PyMuPDF`` Document instance.
            settings (dict): Parsing parameters.
        '''
        # ---------------------------------------------
        # 0. extract fonts properties, especially line height ratio
        # ---------------------------------------------
        fonts = Fonts.extract(fitz_doc)

        # ---------------------------------------------
        # 1. extract and then clean up raw page
        # ---------------------------------------------
        pages, raw_pages = [], []
        words_found = False
        for page in self:
            if page.skip_parsing: continue

            # init and extract data from PDF
            raw_page = RawPageFactory.create(page_engine=fitz_doc[page.id], backend='PyMuPDF')
            raw_page.restore(**settings)

            # # check if any words are extracted since scanned pdf may be directed
            if not words_found and raw_page.raw_text.strip():
                words_found = True

            # process blocks and shapes based on bbox
            raw_page.clean_up(**settings)

            # process font properties
            raw_page.process_font(fonts)


            # after this step, we can get some basic properties
            # NOTE: floating images are detected when cleaning up blocks, so collect them here
            page.width = raw_page.width
            page.height = raw_page.height
            page.float_images.reset().extend(raw_page.blocks.floating_image_blocks)

            raw_pages.append(raw_page)
            pages.append(page)

        # show message if no words found
        if not words_found:
            logging.warning('Words count: 0. It might be a scanned pdf, which is not supported yet.')

        
        # ---------------------------------------------
        # 2. parse structure in document/pages level
        # ---------------------------------------------
        # NOTE: blocks structure might be changed in this step, e.g. promote page header/footer,
        # so blocks structure based process, e.g. calculating margin, parse section should be 
        # run after this step.
        header, footer = Pages._parse_document(raw_pages)


        # ---------------------------------------------
        # 3. parse structure in page level, e.g. page margin, section
        # ---------------------------------------------
        # parse sections
        for page, raw_page in zip(pages, raw_pages):
            # page margin
            margin = raw_page.calculate_margin(**settings)
            raw_page.margin = page.margin = margin

            # page section
            sections = raw_page.parse_section(**settings)
            page.sections.extend(sections)

    def parse_images(self,json_converter_result_list,fitz_doc,filename_pdf, **settings):
        '''Analyse document structure, e.g. page section, header, footer.

        Args:
            fitz_doc (fitz.Document): ``PyMuPDF`` Document instance.
            settings (dict): Parsing parameters.
        '''
        # ---------------------------------------------
        # 0. extract fonts properties, especially line height ratio
        # ---------------------------------------------
        fonts = Fonts.extract(fitz_doc)

        # ---------------------------------------------
        # 1. extract and then clean up raw page
        # ---------------------------------------------
        pages, raw_pages = [], []
        words_found = False
        for pg_num,page in enumerate(self):
            if page.skip_parsing: continue


            ###layout_info 转换成raw_dict的格式
            [img_num, use_flag, items]=json_converter_result_list[pg_num]
            layout_data=items['layout_info']
            hw_info=items['img_height_width']
            lines_infos_list=items['lines_infos_list']


            raw_dict=self.convert_layout2rawdict(layout_data,lines_infos_list,hw_info)
            # import json
            # pdb.set_trace()
            # json.dumps(raw_dict, ensure_ascii=False)

            # ######保存raw_dict到json中###########################
            # import json,os
            # tmp_img_dir='./test_imgs_result_gen/pdf_imgs'
            # json_file_name=filename_pdf.split('/')[-1].replace('.pdf','')
            # json_file_path=os.path.join(tmp_img_dir,json_file_name,json_file_name+'_page'+str(pg_num)+'.json')
            # json_file=open(json_file_path, 'w', encoding='utf-8')
            # json.dump(raw_dict, json_file, ensure_ascii=False)
            # json_file.close()


            # init and extract data from PDF
            #如果字符串为空，则不解释进来
            raw_page = RawPageFactory.create(page_engine=fitz_doc[page.id], backend='PyMuPDF')
            raw_page.restore_image(raw_dict,**settings)
            # raw_page.restore(**settings)
            #

            # check if any words are extracted since scanned pdf may be directed
            # if not words_found and raw_page.raw_text.strip():
            #     words_found = True
            words_found = True

            raw_page.clean_up_table(**settings)
            table_blocks_array = raw_page.blocks.table_blocks

            # process blocks and shapes based on bbox
            raw_page.clean_up(**settings)

            # process font properties
            raw_page.process_font(fonts)
            raw_page.blocks.assign_to_tables(table_blocks_array)


            # after this step, we can get some basic properties
            # NOTE: floating images are detected when cleaning up blocks, so collect them here
            page.width = raw_page.width
            page.height = raw_page.height
            page.float_images.reset().extend(raw_page.blocks.floating_image_blocks)

            raw_pages.append(raw_page)
            pages.append(page)

        # show message if no words found
        if not words_found:
            logging.warning('Words count: 0. It might be a scanned pdf, which is not supported yet.')

        # ---------------------------------------------
        # 2. parse structure in document/pages level
        # ---------------------------------------------
        # NOTE: blocks structure might be changed in this step, e.g. promote page header/footer,
        # so blocks structure based process, e.g. calculating margin, parse section should be
        # run after this step.
        header, footer = Pages._parse_document(raw_pages)

        # ---------------------------------------------
        # 3. parse structure in page level, e.g. page margin, section
        # ---------------------------------------------
        # parse sections
        for page, raw_page in zip(pages, raw_pages):
            # page margin
            if page.skip_parsing:
                continue

            margin = raw_page.calculate_margin(**settings)
            raw_page.margin = page.margin = margin

            table_blocks_array = raw_page.blocks.table_blocks

            #####返回传递的参数
            [img_num, use_flag, items] = json_converter_result_list[page.id]
            sections_count_list=items['sections_count_list']
            columns_count_list = items['columns_count_list']

            if(len(sections_count_list)==0):   ##单版面
                # page section
                sections = raw_page.parse_section(**settings)
            else:
                # page section
                sections = raw_page.parse_section_DoubleLayout(sections_count_list,columns_count_list,**settings)
                # sections = raw_page.parse_section(**settings)


            ##将sections——》section——》Columns——》Column.blocks._instances中的Line中，在表格内的进行转换
            ##转换成TableBlock
            ###将TableBlock 归类回到sections中
            sections = raw_page.parse_section_Table_sort(table_blocks_array,sections, **settings)

            page.sections.extend(sections)



    def init_dict_version(self):
        self.raw_dict_init = {}
        self.raw_dict_init.update({"width": 724, "height": 1024, "shapes": [], "blocks": []})

        self.shapes_unit_line_init = {}
        self.shapes_unit_line_init.update({"start": [], "end": [], "width": 1.0, "color": 9605778})

        self.shapes_unit_box_init = {}
        self.shapes_unit_box_init.update({"bbox": [], "color": 14671839})

        self.shapes_unit_url_init = {}
        self.shapes_unit_url_init.update({"type": 8,"bbox": [], "uri": ""})

        self.new_blcok_dict_img_init = {}
        self.new_blcok_dict_img_init.update(
            {"type": 1, "bbox": [], "width": '', "height": '', "image": ''})  ######type=1 表示图像

        self.new_blcok_dict_text_init = {}
        self.new_blcok_dict_text_init.update({"number": 0, "type": 0, "bbox": [], "lines": []})  ######type=0 表示文本

        self.lines_dict_text_init = {}
        self.lines_dict_text_init.update({"spans": '', "wmode": 0, "bbox": [], "dir": [1.0, 0.0]})

        self.spans_dict_text_init = {}
        # spans_dict_text_init.update({"size": 9.0, "flags": 4, "font": "SimSun", "color": 0, "ascender":1.0529999732971191, "descender": -0.2809999883174896, "chars": '', "origin": [], "bbox": []})
        self.spans_dict_text_init.update(
            {"size": 9.0, "flags": 4, "font": "SimSun", "color": 0, "ascender": 1.0529999732971191,
             "descender": -0.2809999883174896, "chars": '', "origin": [],"label":"TEXT", "bbox": []})

        self.chars_init = {}
        self.chars_init.update({"origin": [], "bbox": [], "c": ''})

        ###字典顺序问题
        ## raw_dict_init["shapes"]=[shapes_unit_init]
        #  raw_dict_init["blocks"]=[new_blcok_dict_text_init]
        #  new_blcok_dict_text_init["lines"]=[lines_dict_text_init]
        #  lines_dict_text_init["spans"]=[spans_dict_text_init]
        #  spans_dict_text_init["chars"]=[chars_init]
        self.shapes_unit_init=[self.shapes_unit_line_init,self.shapes_unit_box_init,self.shapes_unit_url_init]


        self.table_block_init= {}
        self.table_block_init.update(
            {"type": 2, "bbox": [], "rows": []})  ######type=1 表示图像   type=2 有线  type=3 无线

        self.table_block_row_info_init = {}
        self.table_block_row_info_init.update(
            {"bbox": [], "height": 1.0,"cells":[]})  ######row

        self.table_block_cell_info_init = {}
        self.table_block_cell_info_init.update(
            {"bbox": [0,0,0,0], "border_color": [0,0,0,0],"bg_color":None,"border_width":[1.0,1.0,1.0,1.0],'merged_cells': [1,1],'blocks':[]})         #border_color【四条线的color】



    def explain_table_dict_version(self, coord_new, table_infoes, table_texts_fonts):

        # LATTICE_TABLE = 2   #有线
        # STREAM_TABLE = 3    #无线

        table_block_init = self.table_block_init.copy()

        rows_num = table_infoes['form_rows']
        cols_num = table_infoes['form_columns']
        rows_height = table_infoes['rows_height']
        cols_width = table_infoes['cols_width']

        cells_infos = table_infoes['form_blocks']
        table_block_init["bbox"] = coord_new
        text_fonts_num=0

        rows = []
        current_row=0

        cells = []
        cells_x = []
        cells_y = []
        current_row_text_array=[]

        print("table_texts_fonts: len: {}".format(len(table_texts_fonts)))
        print("Table  rows_num:{}    cols_num:{}".format(rows_num,cols_num))

        for cell_info in cells_infos:
            start_row=cell_info["start_row"]
            end_row = cell_info["end_row"]
            start_column = cell_info["start_column"]
            end_column = cell_info["end_column"]

            ##save current rows
            if(current_row!=start_row ):
                row_dict_init = self.table_block_row_info_init.copy()  ##当前row 解析
                row_dict_init["bbox"] = [min(cells_x), min(cells_y), max(cells_x), max(cells_y)]
                row_dict_init["height"] = rows_height[current_row]/ self.init_height * self.height
                print("cells: num:{}".format(len(cells)))
                if(len(cells)<cols_num):
                    ##add empty cell
                    cur_cell_num=len(cells)
                    while(cur_cell_num<cols_num):
                        # blocks=[]
                        # block_text_dict = self.explain_text_dict([0,0,0,0], [0,0,0,0], '', 'Text')
                        # blocks.append(block_text_dict)
                        cell = self.table_block_cell_info_init.copy()
                        # cell["blocks"]=blocks
                        cells.append(cell)
                        cur_cell_num=cur_cell_num+1

                row_dict_init["cells"] = cells
                rows.append(row_dict_init)

                print(current_row_text_array)
                print()
                current_row = start_row
                cells = []
                cells_x = []
                cells_y = []
                current_row_text_array = []

            print("start_row:{}  end_row:{}   start_column:{}    end_column:{}   current_row:{}".format(start_row,
                                                                                                        end_row,
                                                                                                        start_column,
                                                                                                        end_column,
                                                                                                        current_row))
            # multi text
            blocks = []
            for cell_info_text in cell_info["lines"]:
                text = cell_info_text["text"]
                current_row_text_array.append(text)
                co = cell_info_text["poly"][0:8]
                text_coord = [min(co[::2]), min(co[1::2]), max(co[::2]), max(co[1::2])]

                text_coord_new = [int(text_coord[0] / self.init_width * self.width),
                                  int(text_coord[1] / self.init_height * self.height),
                                  int(text_coord[2] / self.init_width * self.width),
                                  int(text_coord[3] / self.init_height * self.height)]


                try:
                    box_label = table_texts_fonts[text_fonts_num]
                except:
                    box_label=[]
                label = 'Text'
                block_text_dict = self.explain_text_dict(box_label, text_coord_new, text, label)

                blocks.append(block_text_dict)
                text_fonts_num = text_fonts_num + 1


            ####当前cell的属性
            cell = self.table_block_cell_info_init.copy()
            coord_org = cell_info["org_position"]
            coord=[min(coord_org[::2]), min(coord_org[1::2]), max(coord_org[::2]), max(coord_org[1::2])]
            cell_coord_new = [int(coord[0] / self.init_width * self.width),
                              int(coord[1] / self.init_height * self.height),
                              int(coord[2] / self.init_width * self.width),
                              int(coord[3] / self.init_height * self.height)]

            cell["bbox"] = cell_coord_new
            cell['merged_cells'] =[end_row-start_row+1, end_column-start_column+1]
            cell['logis_cells'] = [start_row, start_column, end_row, end_column]
            cell["blocks"] = blocks
            cells.append(cell)

            cells_x.append(cell_coord_new[0])
            cells_x.append(cell_coord_new[2])
            cells_y.append(cell_coord_new[1])
            cells_y.append(cell_coord_new[3])


        row_dict_init = self.table_block_row_info_init.copy()  ##当前row 解析
        row_dict_init["bbox"] = [min(cells_x), min(cells_y), max(cells_x), max(cells_y)]
        row_dict_init["height"] = rows_height[current_row] / self.init_height * self.height
        if (len(cells) < cols_num):
            ##add empty cell
            cur_cell_num = len(cells)
            while (cur_cell_num < cols_num):
                # blocks = []
                # block_text_dict = self.explain_text_dict([0, 0, 0, 0], [0, 0, 0, 0], '', 'Text')
                # blocks.append(block_text_dict)
                cell = self.table_block_cell_info_init.copy()
                # cell["blocks"] = blocks
                cells.append(cell)
                cur_cell_num = cur_cell_num + 1

        row_dict_init["cells"] = cells
        rows.append(row_dict_init)
        print(current_row_text_array)

        # pdb.set_trace()
        table_block_init["rows"] = rows
        return table_block_init

    def explain_table_dict_version_old_dao2(self, coord_new, table_infoes, table_texts_fonts):
        # LATTICE_TABLE = 2   #有线
        # STREAM_TABLE = 3    #无线

        table_block_init = self.table_block_init.copy()

        rows_num = table_infoes['form_rows']
        cols_num = table_infoes['form_columns']
        rows_height = table_infoes['rows_height']
        cols_width = table_infoes['cols_width']

        cells_infos = table_infoes['form_blocks']
        table_block_init["bbox"] = coord_new
        text_fonts_num=0

        print(cells_infos)
        print(len(cells_infos))

        ###have not merge cell
        rows = []
        for row_id in range(rows_num):

            row_dict_init = self.table_block_row_info_init.copy()  ##当前row 解析
            cells = []

            cells_x = []
            cells_y = []


            for cell_id in range(cols_num):

                print(row_id * cols_num + cell_id)
                cell_infos = cells_infos[row_id * cols_num + cell_id]

                #multi text
                blocks = []

                for cell_info in cell_infos["lines"]:
                    text=cell_info["text"]
                    co=cell_info["poly"]
                    text_coord=[min(co[::2]),min(co[1::2]),max(co[::2]),max(co[1::2])]

                    text_coord_new = [int(text_coord[0] / self.init_width * self.width), int(text_coord[1] / self.init_height * self.height),
                                 int(text_coord[2] / self.init_width * self.width), int(text_coord[3] / self.init_height * self.height)]


                    box_label=table_texts_fonts[text_fonts_num]
                    if (len(text.strip()) == 0):
                        box_label=[]
                    label='Text'
                    block_text_dict = self.explain_text_dict(box_label, text_coord_new, text, label)
                    blocks.append(block_text_dict)
                    text_fonts_num=text_fonts_num+1


                ####当前cell的属性
                cell = self.table_block_cell_info_init.copy()
                coord = cell_infos["position"]
                cell_coord_new = [int(coord[0] / self.init_width * self.width),
                                  int(coord[1] / self.init_height * self.height),
                                  int(coord[2] / self.init_width * self.width),
                                  int(coord[3] / self.init_height * self.height)]

                cell["bbox"] =cell_coord_new
                cell['merged_cells'] = [1, 1]
                cell["blocks"] = blocks
                cells.append(cell)

                cells_x.append(cell_coord_new[0])
                cells_x.append(cell_coord_new[2])
                cells_y.append(cell_coord_new[1])
                cells_y.append(cell_coord_new[3])

            row_dict_init["bbox"] = [min(cells_x), min(cells_y), max(cells_x), max(cells_y)]
            row_dict_init["height"] = rows_height[row_id]/ self.init_height * self.height
            row_dict_init["cells"] = cells
            rows.append(row_dict_init)

        table_block_init["rows"] = rows
        return table_block_init

    def explain_table_dict_version_old(self,coord_new,table_infoes,table_texts_fonts):
        # LATTICE_TABLE = 2   #有线
        # STREAM_TABLE = 3    #无线

        table_block_init=self.table_block_init.copy()


        # table_json='./test_imgs_result_gen/nanjing_page6_table.json'
        # with open(table_json, 'r', encoding='utf-8') as path_json:
        #     table_infoes = json.load(path_json)


        rows_num = table_infoes['rows']
        cols_num = table_infoes['cols']
        cells_infos = table_infoes['cells_infoes']

        table_block_init["bbox"] = coord_new
        rows = []
        for row_id in range(rows_num):

            row_dict_init=self.table_block_row_info_init.copy()    ##当前row 解析
            cells=[]

            cells_x = []
            cells_y = []

            for cell_id in range(cols_num):
                 cell_infos = cells_infos[row_id * cols_num + cell_id]
                 # pdb.set_trace()

                 ####single text or multi text

                 ##cell coord from combine texts
                 cell_x=[]
                 cell_y=[]

                 text = cell_infos["text"]
                 coord = cell_infos["bbox"]
                 cell_coord_new = [int(coord[0] / self.init_width * self.width),
                                   int(coord[1] / self.init_height * self.height),
                                   int(coord[2] / self.init_width * self.width),
                                   int(coord[3] / self.init_height * self.height)]


                 cell_x.append(cell_coord_new[0])
                 cell_x.append(cell_coord_new[2])
                 cell_y.append(cell_coord_new[1])
                 cell_y.append(cell_coord_new[3])

                 box_label = coord
                 label = 'Text'
                 block_text_dict = self.explain_text_dict(box_label, cell_coord_new, text, label)
                 blocks = []
                 blocks.append(block_text_dict)
                 # pdb.set_trace()


                 ##multi text
                 # for cell_info in cell_infos:
                 #     text=cell_info["text"]
                 #     coord=cell_info["bbox"]
                 #     cell_coord_new = [int(coord[0] / self.init_width * self.width), int(coord[1] / self.init_height * self.height),
                 #                  int(coord[2] / self.init_width * self.width), int(coord[3] / self.init_height * self.height)]
                 #
                 #     cell_x.append(cell_coord_new[0],cell_coord_new[2])
                 #     cell_y.append(cell_coord_new[1], cell_coord_new[3])
                 #
                 #     box_label=coord
                 #     label='Text'
                 #     block_text_dict = self.explain_text_dict(box_label, cell_coord_new, text, label)
                 #     blocks.append(block_text_dict)


                 cell=self.table_block_cell_info_init.copy()

                 cell["bbox"] = [min(cell_x),min(cell_y),max(cell_x),max(cell_y)]
                 cell['merged_cells']=[1,1]
                 cell["blocks"]=blocks
                 cells.append(cell)

                 cells_x.append(min(cell_x))
                 cells_x.append(max(cell_x))
                 cells_y.append(min(cell_y))
                 cells_y.append(max(cell_y))


            row_dict_init["bbox"]=[min(cells_x),min(cells_y),max(cells_x),max(cells_y)]
            row_dict_init["height"]=max(cells_y)-min(cells_y)
            row_dict_init["cells"]=cells
            rows.append(row_dict_init)

        table_block_init["rows"]=rows
        return table_block_init

    def explain_text_dict(self,box_label,coord_new,text,label):
        block_text_dict = self.new_blcok_dict_text_init.copy()
        lines_dict_text = self.lines_dict_text_init.copy()
        spans_dict_text = self.spans_dict_text_init.copy()
        chars_dict = self.chars_init.copy()

        # chars_dict_array=[]
        if(isinstance(box_label, dict) and "font_label" in box_label):
            font = box_label["font_label"]
            size = box_label["size_label"]
            color = box_label["color_label"]
            bold_label = box_label["bold_label"]
            italic_label = box_label["italic_label"]
            underline_label = box_label["underline_label"]
            middleline_label = box_label["middleline_label"]
        else:
            font ='DEFAULT'
            size =9.0
            color = '黑'


        chars_dict["origin"] = coord_new[0:2]
        chars_dict["bbox"] = coord_new
        chars_dict["c"] = text

        spans_dict_text["chars"] = [chars_dict]
        spans_dict_text["origin"] = coord_new[0:2]
        spans_dict_text["bbox"] = coord_new

        # size = 12
        spans_dict_text["size"] = float(size)
        spans_dict_text["label"] = label

        # font_list = ['DEFAULT', '宋体', '黑体', '楷体', '仿宋', 'TIMESNEWROMAN', 'ARIAL']
        # color_list = ['黑', '蓝', '红', '白']
        #
        # font_conver_list = ['SimSun', 'SimSun', 'SimHei', 'SimKai', 'SimFang', 'TimesNewRomanPSMT', 'ARIAL']
        # color_conver_list = [0, 32640, 16711680, 16581375]

        # if (font != "DEFAULT"):
        #     font_idx = font_list.index(font)
        #     spans_dict_text["font"] = font_conver_list[font_idx]

        #
        # color_idx = color_list.index(color)
        # spans_dict_text["color"] = color_conver_list[color_idx]
        spans_dict_text["font"] = font
        spans_dict_text["color"] = 0

        lines_dict_text["spans"] = [spans_dict_text]
        lines_dict_text["bbox"] = coord_new

        block_text_dict["bbox"] = coord_new
        block_text_dict["lines"] = [lines_dict_text]

        return block_text_dict



    def convert_layout2rawdict(self,layout_data,lines_infos_list,hw_info):

        ###initial the dict
        self.init_dict_version()
        raw_dict_init=self.raw_dict_init.copy()
        shapes_unit_init=self.shapes_unit_init.copy()
        new_blcok_dict_img_init=self.new_blcok_dict_img_init.copy()
        new_blcok_dict_text_init=self.new_blcok_dict_text_init.copy()
        lines_dict_text_init=self.lines_dict_text_init.copy()
        spans_dict_text_init=self.spans_dict_text_init.copy()
        chars_init=self.chars_init.copy()


        raw_dict = raw_dict_init.copy()

        ##resize img
        self.width = 618.3200073242188
        self.height = 841.9199829101562

        # self.width = 614
        # self.height = 792

        [self.init_height,self.init_width]=hw_info



        raw_dict["width"] = self.width
        raw_dict["height"] = self.height

        header_array = []
        footer_array = []

        blocks_array=[]
        for box_num,box_label in enumerate(layout_data):
            block_text_dict = new_blcok_dict_text_init.copy()
            print(box_label)
            coord=box_label["coord"]   ##[左上角(x,y),右下角(x,y)]  #每行文本的原始数据

            # if(abs(coord[2]-500)<18):  ##右边点为500   左边点536
            #     coord[2]=500
            #
            # if (abs(coord[0] - 536) < 18):  ##右边点为500   左边点536
            #     coord[0] = 536

            coord_new=[int(coord[0]/self.init_width*self.width),int(coord[1]/self.init_height*self.height),int(coord[2]/self.init_width*self.width),int(coord[3]/self.init_height*self.height)]   #resize

            label = box_label["label"]


            ##原始数据里有table，需要转换成TableBlock
            if(label=="Table"):
                ##add by chen in 20220621
                #初始化为blocks
                ##按table的字典格式输出

                table_infoes,table_texts_fonts=box_label["text"]
                table_block=self.explain_table_dict_version(coord_new,table_infoes,table_texts_fonts)

                blocks_array.append(table_block)
                continue

            if(label=="Figure"):
                block_img_dict = new_blcok_dict_img_init.copy()
                figure_img_base64 = box_label["text"]

                # FLOAT_IMAGE = 4         #悬浮图

                new_blcok_dict_img_init.update(
                    {"type": 1, "bbox": [], "width": '', "height": '', "image": ''})  ######type=1 表示图像

                block_img_dict["type"]=1
                block_img_dict["bbox"] = coord_new
                block_img_dict["width"] =int(coord_new[2]-coord_new[0])
                block_img_dict["height"] = int(coord_new[3]-coord_new[1])
                block_img_dict["image"] = figure_img_base64

                blocks_array.append(block_img_dict)
                continue

            if(label=="Header" or label == "sectionHeading"):
                header_array.append(coord)

            if(label=="Footer"):
                footer_array.append(coord)


            text = box_label["text"].strip()

            ###if label is text ,then replain as text blocks
            block_text_dict=self.explain_text_dict(box_label, coord_new, text, label)
            blocks_array.append(block_text_dict)

        raw_dict["blocks"]=blocks_array
        shapes_array = []
        # [shapes_unit_line_init, shapes_unit_box_init, shapes_unit_url_init]=shapes_unit_init
        # [rowboxes, colboxes]=lines_infos_list
        #
        # for rowbox in rowboxes:   ###横线
        #     shapes_unit_init=shapes_unit_line_init.copy()
        #     shapes_unit_init["start"]=[rowbox[0],rowbox[1]]
        #     shapes_unit_init["end"] = [rowbox[2], rowbox[3]]
        #     shapes_array.append(shapes_unit_init)
        #
        # for colbox in colboxes:   ###竖线
        #     shapes_unit_init=shapes_unit_line_init.copy()
        #     shapes_unit_init.update({"start": [], "end": [], "width": 1.0, "color": 9605778})
        #     shapes_unit_init["start"]=[colbox[0],colbox[1]]
        #     shapes_unit_init["end"] = [colbox[2], colbox[3]]
        #     shapes_array.append(shapes_unit_init)

        # json_file=open("./raw_dict0630_page1.json", 'w', encoding='utf-8')
        # json.dump(raw_dict, json_file, ensure_ascii=False)
        # json_file.close()
        # pdb.set_trace()

        return raw_dict


    @staticmethod
    def _parse_document(raw_pages:list):
        '''Parse structure in document/pages level, e.g. header, footer'''
        # TODO
        return '', ''