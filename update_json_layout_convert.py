
import json

class LayoutConvertFormat:

    def __init__(self, img_width=1224, img_height=1584):
        self.img_width = img_width
        self.img_height = img_height

    def calculate_iou(delf, box1, box2):
        """
        Calculate the Intersection over Union (IOU) between two bounding boxes.

        Parameters:
            box1 (tuple): Coordinates of the first bounding box (x1, y1, x2, y2).
            box2 (tuple): Coordinates of the second bounding box (x1, y1, x2, y2).

        Returns:
            float: IOU value.
        """
        x1, y1, x2, y2 = box1
        x3, y3, x4, y4 = box2

        # Calculate the area of intersection
        inter_x1 = max(x1, x3)
        inter_y1 = max(y1, y3)
        inter_x2 = min(x2, x4)
        inter_y2 = min(y2, y4)
        inter_area = max(0, inter_x2 - inter_x1 + 1) * max(0, inter_y2 - inter_y1 + 1)

        # Calculate the area of union
        box1_area = (x2 - x1 + 1) * (y2 - y1 + 1)
        box2_area = (x4 - x3 + 1) * (y4 - y3 + 1)

        # Take the smaller area region
        # union_area = box1_area + box2_area - inter_area
        union_area = min(box1_area, box2_area)

        # Check for zero union area
        if union_area == 0:
            return False  # Can't divide by zero, return False indicating no overlap

        # Calculate IOU
        iou = inter_area / union_area

        if iou > 0.2:
            return True
        else:
            return False

    def calculate_gaps(self, lst):
        return [lst[i + 1] - lst[i] for i in range(len(lst) - 1)]

    def bbox_pdf_convert_image(self, polygon, pdf_width, pdf_height):
        """
        # Coordinate transformation: PDF -> Image
        """
        text_coord = [polygon[0]['x'], polygon[0]['y'], polygon[2]['x'], polygon[2]['y']]
        text_coord_new = [int(text_coord[0] / pdf_width * self.img_width),
                          int(text_coord[1] / pdf_height * self.img_height),
                          int(text_coord[2] / pdf_width * self.img_width),
                          int(text_coord[3] / pdf_height * self.img_height)]
        return text_coord_new

    def filter_similar_elements(self, input_list, threshold):
        filtered_list = [input_list[0]]  # Initialize the result list and add the first element to it
        for i in range(1, len(input_list)):
            # Check the difference between the current element and the last element in the result list
            diff = abs(input_list[i] - filtered_list[-1])
            if diff >= threshold:
                filtered_list.append(input_list[i])
        return filtered_list

    def pages_parse(self, pages_json):
        pages_dict = {}
        for page_json in pages_json:
            page_number = page_json['page_number']
            pdf_width = page_json['width']
            pdf_height = page_json['height']
            lines = page_json['lines']
            page_lines = []
            for line in lines:

                role = line.get('role', 'title')
                if role==None:
                    role = 'title'
                    # print('role: {}'.format(role))

                text = line.get('content', '')
                polygon = line.get('polygon', [])

                # Coordinate transformation: PDF -> Image
                text_coord = self.bbox_pdf_convert_image(polygon, pdf_width, pdf_height)

                spans = line.get('spans', [])

                Font = line.get('Font', "TimesNewRomanPSMT")
                if Font == None:
                    # print("Font: {}".format(Font))
                    Font = "TimesNewRomanPSMT"

                Font_Size = line.get('Font Size', 12.0)
                if Font_Size==None:
                    # print("font size: {}".format(Font_Size))
                    Font_Size = 12.0

                info = {}
                info['coord'] = text_coord
                info['label'] = role
                info['text'] = text
                info['font_label'] = Font
                info['size_label'] = Font_Size
                info['spans'] = spans
                info['color_label'] = "black"
                info['bold_label'] = "none"
                info['italic_label'] = "italic"
                info['underline_label'] = "underline"
                info['middleline_label'] = "none"
                page_lines.append(info.copy())
            pages_dict[page_number] = {'width': pdf_width, 'height': pdf_height, 'lines': page_lines}
        return pages_dict

    def paragraphs_parse(self, paragraphs_json, pages_dict):
        paragraphs_dict = {}
        for paragraph_json in paragraphs_json:
            role = paragraph_json['role']
            text = paragraph_json['content']
            page_number = paragraph_json['bounding_regions'][0]['page_number']
            polygon = paragraph_json['bounding_regions'][0]['polygon']
            pdf_width = pages_dict[page_number]['width']
            pdf_height = pages_dict[page_number]['height']
            # text_coord = [polygon[0]['x'], polygon[0]['y'], polygon[2]['x'], polygon[2]['y']]
            text_coord = self.bbox_pdf_convert_image(polygon, pdf_width, pdf_height)
            if page_number not in paragraphs_dict:
                paragraphs_dict[page_number] = []
            paragraph_element = {'role': role, 'text': text, 'polygon': text_coord}
            paragraphs_dict[page_number].append(paragraph_element.copy())
        return paragraphs_dict

    def tables_parse(self, tables_json, pages_dict):
        tables_dict = {}
        for table_json in tables_json:
            cells = table_json['cells']
            rows_points = []
            columns_points = []
            table_cells_list = []
            for cell in cells:
                form_block = {}
                page_number = cell['bounding_regions'][0]['page_number']
                polygon = cell['bounding_regions'][0]['polygon']
                pdf_width = pages_dict[page_number]['width']
                pdf_height = pages_dict[page_number]['height']
                form_block['start_row'] = cell['row_index']
                form_block['start_column'] = cell['column_index']
                form_block['end_row'] = cell['row_index'] + cell['row_span'] - 1
                form_block['end_column'] = cell['column_index'] + cell['column_span'] - 1
                form_block['data'] = cell['content']
                cell_lines = cell['lines']
                lines_list = []
                for cell_line in cell_lines:
                    cell_text = cell_line['content']
                    cell_poly = cell_line['polygon']
                    cell_coord = self.bbox_pdf_convert_image(cell_poly, pdf_width, pdf_height)
                    lines_list.append({'text': cell_text,
                                       'poly': [cell_coord[0], cell_coord[1],
                                                cell_coord[2], cell_coord[1],
                                                cell_coord[2], cell_coord[3],
                                                cell_coord[2], cell_coord[3], 0.98],
                                       'score': 0.98,
                                       'char_centers': [],
                                       'char_polygons': [],
                                       'char_candidates': [],
                                       'char_candidates_score': [],
                                       'char_scores': []
                                       })

                form_block['lines'] = lines_list

                text_coord = self.bbox_pdf_convert_image(polygon, pdf_width, pdf_height)
                # text_coord = [polygon[0]['x'], polygon[0]['y'], polygon[2]['x'], polygon[2]['y']]
                form_block['polygon'] = text_coord
                spans = cell['spans']
                form_block['spans'] = spans
                table_cells_list.append(form_block.copy())

                #
                if text_coord[0] not in columns_points:
                    columns_points.append(text_coord[0])
                if text_coord[2] not in columns_points:
                    columns_points.append(text_coord[2])
                if text_coord[1] not in rows_points:
                    rows_points.append(text_coord[1])
                if text_coord[3] not in rows_points:
                    rows_points.append(text_coord[3])

            # for cell in cells:
            rows_points = sorted(rows_points)
            columns_points = sorted(columns_points)
            rows_points = self.filter_similar_elements(rows_points, 15)
            columns_points = self.filter_similar_elements(columns_points, 15)

            row_count = table_json['row_count']
            column_count = table_json['column_count']
            page_number = table_json['bounding_regions'][0]['page_number']
            polygon = table_json['bounding_regions'][0]['polygon']
            spans = table_json['spans']
            text_coord = self.bbox_pdf_convert_image(polygon, pdf_width, pdf_height)

            if page_number not in tables_dict:
                tables_dict[page_number] = []
            tables_dict[page_number].append({'row_count': row_count, 'column_count': column_count,
                                             'rows_points': rows_points, 'columns_points': columns_points,
                                             'polygon': text_coord, 'spans': spans, 'cells': table_cells_list})
        return tables_dict

    def pages_label_classify(self, tables_dict, pages_dict):
        """
        # Divide the content within pages into table area elements and non-table area elements
        """
        res_list = []
        for page_number in pages_dict:
            page_info = {}
            layout_info = []
            # Check if the page contains a table
            if page_number not in tables_dict:
                # Does not contain a table
                pages_page_number = pages_dict[page_number]
                page_page_number_lines = pages_page_number['lines']
                for num, page_page_number_line in enumerate(page_page_number_lines):

                    # Text parsing
                    layout_info.append(page_page_number_line)
                    # pass
            else:
                # Contains a table
                tables_page_number = tables_dict[page_number]
                pages_page_number = pages_dict[page_number]
                page_page_number_lines = pages_page_number['lines']
                table_text_list = []
                page_index_label = [0] * len(page_page_number_lines)
                # Traverse the table
                for table_page_number in tables_page_number:
                    table_page_number_cells = table_page_number['cells']
                    form_blocks = []

                    # Iterate through table cells
                    for table_page_number_cell in table_page_number_cells:

                        cell_text = table_page_number_cell['data']
                        cell_polygon = table_page_number_cell['polygon']
                        form_blocks_lines = []

                        # Iterate through the content in the page element, match with cell elements
                        for num, page_page_number_line in enumerate(page_page_number_lines):
                            page_text = page_page_number_line['text']
                            page_polygon = page_page_number_line['coord']
                            iou_flag = self.calculate_iou(page_polygon, cell_polygon)

                            # Match elements in the table by text and box IOU
                            if page_text.strip() in cell_text and iou_flag:

                                line_dict = {'text': page_text,
                                              'poly': [page_polygon[0], page_polygon[1], page_polygon[2],
                                                       page_polygon[1],
                                                       page_polygon[2], page_polygon[3], page_polygon[2],
                                                       page_polygon[3], 0.98],
                                              'score': 0.98,
                                              'char_centers': [],
                                              'char_polygons':[],
                                              'char_candidates':[],
                                              'char_candidates_score':[],
                                              'char_scores':[]
                                            }

                                form_blocks_lines.append(line_dict.copy())

                                table_text_list.append(page_page_number_line.copy())

                                page_index_label[num] = 1

                        table_page_number_cell['data'] = cell_text
                        table_page_number_cell['position'] = cell_polygon
                        table_page_number_cell['org_position'] = cell_polygon
                        table_page_number_cell['char_position'] = [cell_polygon]
                        table_page_number_cell['lines'] = form_blocks_lines
                        form_blocks.append(table_page_number_cell.copy())

                    rows_points = table_page_number['rows_points']
                    columns_points = table_page_number['columns_points']
                    position = [min(columns_points), min(rows_points), max(columns_points), max(rows_points)]
                    org_position = [position[0], position[1], position[2], position[1], position[2], position[3],
                                    position[0], position[3]]

                    table_structure = {'type': True, 'data': '',
                                       'form_rows': table_page_number['row_count'],
                                       'form_columns': table_page_number['column_count'],
                                       'rows_height': self.calculate_gaps(rows_points), 'cols_width': self.calculate_gaps(columns_points),
                                       'position': position, 'org_position': org_position, 'char_position': [],
                                       'lines': [], 'form_blocks': form_blocks.copy()}

                    res_table_json = {'label': "Table",
                                      'coord': position,
                                      'text': [table_structure, table_text_list]}
                    # Annotate the table
                    layout_info.append(res_table_json.copy())

                for num, page_page_number_line in enumerate(page_page_number_lines):
                    if page_index_label[num] == 0:
                        # Text parsing
                        layout_info.append(page_page_number_line)
                        # pass

            page_info['pg_num'] = page_number - 1
            page_info['layout_info'] = layout_info
            page_info['img_height_width'] = [self.img_height, self.img_width]
            page_info['sections_count_list'] = []
            page_info['columns_count_list'] = []
            page_info['lines_infos_list'] = []
            res_list.append([page_number - 1, True, page_info.copy()])

        return res_list

    def convert_format_main(self, path):
        """
        Main function for parsing JSON
        """
        with open(path, 'r', encoding='utf-8') as js:
            res = json.load(js)

            # Parse 'pages' element
            pages_json = res['pages']
            pages_dict = self.pages_parse(pages_json)

            # Parse 'tables' element
            tables_json = res['tables']
            tables_dict = self.tables_parse(tables_json, pages_dict)

            # Classify elements in 'pages' element into table area elements and non-table area elements
            res_list = self.pages_label_classify(tables_dict, pages_dict)
        return res_list

layout_convert_format = LayoutConvertFormat()

# path = 'datasets/update_CA Infrastructure Fin.json'
# res_list = layout_convert_format.convert_format_main(path)
