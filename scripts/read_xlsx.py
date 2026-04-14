import zipfile
import xml.etree.ElementTree as ET
import sys

def read_xlsx(filename):
    try:
        with zipfile.ZipFile(filename, 'r') as z:
            # Read shared strings
            shared_strings = []
            try:
                with z.open('xl/sharedStrings.xml') as f:
                    tree = ET.parse(f)
                    for si in tree.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
                        t = si.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
                        if t is not None:
                            shared_strings.append(t.text)
            except KeyError:
                pass # No shared strings

            # Read sheet1
            with z.open('xl/worksheets/sheet1.xml') as f:
                tree = ET.parse(f)
                rows = []
                for row in tree.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row'):
                    cells = []
                    for c in row.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c'):
                        v = c.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
                        if v is not None:
                            value = v.text
                            if c.get('t') == 's':
                                value = shared_strings[int(value)]
                            cells.append(value)
                        else:
                            cells.append(None)
                    rows.append(cells)
                return rows
    except Exception as e:
        print(f"Error: {e}")
        return None

data = read_xlsx('organigrama.xlsx')
if data:
    for row in data:
        print(",".join([str(x) if x is not None else "" for x in row]))
