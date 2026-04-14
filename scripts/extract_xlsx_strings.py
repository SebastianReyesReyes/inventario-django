import zipfile
import xml.etree.ElementTree as ET

def extract_strings(filename):
    with zipfile.ZipFile(filename, 'r') as z:
        shared_strings = []
        try:
            with z.open('xl/sharedStrings.xml') as f:
                tree = ET.parse(f)
                for si in tree.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
                    # Text can be in <t> or nested in <r><t>
                    text = ""
                    for t in si.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t'):
                        text += t.text if t.text else ""
                    shared_strings.append(text)
        except KeyError:
            pass
        return shared_strings

strings = extract_strings('organigrama.xlsx')
for s in sorted(list(set(strings))):
    if len(s) > 3: # Ignore small IDs
        print(s)
