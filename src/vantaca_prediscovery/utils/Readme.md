# Generate xml_concat_gui

Install packages if not already. Run the following in {project_root_dir}:

```bash
pip install -r requirements-dev.txt
pyinstaller --onefile --noconsole  src/vantaca_prediscovery/utils/xlsx_concat_gui.py
```


Binary is placed in __dist__ folder.