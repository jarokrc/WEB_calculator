import sys
from pathlib import Path

import pytest

# Ensure `src` is importable when running tests from repo root.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def sample_package():
    from web_calculator.core.models.package import Package

    return Package(code="WEB-START", name="Starter", description="Test", base_price=120.0)


@pytest.fixture
def sample_service():
    from web_calculator.core.models.service import Service

    return Service(
        code="WEB-BLOG",
        label="Blog",
        source="WEB",
        unit="ks",
        price=50.0,
        tag="CONTENT",
        info="Simple blog",
    )


@pytest.fixture
def minimal_excel(tmp_path):
    """
    Vytvori miniaturny XLSX archiv so sheetom `_DATA`.
    Staci na overenie parsovania `load_catalog_from_excel`.
    """
    import zipfile

    shared_strings = """<?xml version="1.0" encoding="UTF-8"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="11" uniqueCount="11">
  <si><t>PKG</t></si>
  <si><t>Starter</t></si>
  <si><t>CMS</t></si>
  <si><t>Backend</t></si>
  <si><t>Note</t></si>
  <si><t>Desc</t></si>
  <si><t>Service A</t></si>
  <si><t>WEB</t></si>
  <si><t>CAT</t></si>
  <si><t>od</t></si>
  <si><t>Info</t></si>
</sst>
"""

    workbook = """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="_DATA" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>
"""

    relationships = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>
"""

    sheet = """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1">
      <c r="A1" t="s"><v>0</v></c>
      <c r="B1" t="s"><v>1</v></c>
      <c r="C1"><v>100.5</v></c>
      <c r="D1" t="s"><v>2</v></c>
      <c r="E1" t="s"><v>3</v></c>
      <c r="F1" t="s"><v>4</v></c>
      <c r="G1" t="s"><v>5</v></c>
    </row>
    <row r="2">
      <c r="K2" t="s"><v>6</v></c>
      <c r="J2" t="s"><v>7</v></c>
      <c r="L2" t="s"><v>9</v></c>
      <c r="M2"><v>10</v></c>
      <c r="N2" t="s"><v>10</v></c>
      <c r="O2" t="s"><v>8</v></c>
    </row>
  </sheetData>
</worksheet>
"""

    path = tmp_path / "mini.xlsx"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("xl/sharedStrings.xml", shared_strings)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", relationships)
        zf.writestr("xl/worksheets/sheet1.xml", sheet)
    return path
