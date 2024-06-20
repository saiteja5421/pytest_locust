"""Generate the code pages."""

from pathlib import Path
import shutil
import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()

for path in sorted(Path("tests/steps/").rglob("*.py")):
    module_path = path.relative_to("").with_suffix("")
    doc_path = path.relative_to("").with_suffix(".md")
    full_doc_path = Path("reference", doc_path)
    parts = list(module_path.parts)

    if parts[-1] == "__init__":
        parts = parts[:-1]
        doc_path = doc_path.with_name("index.md")
        full_doc_path = full_doc_path.with_name("index.md")
    elif parts[-1] == "__main__":
        continue

    nav[parts] = doc_path.as_posix()

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        identifier = ".".join(parts)
        print("::: " + identifier, file=fd)
    mkdocs_gen_files.set_edit_path(full_doc_path, path)

with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())

nav2 = mkdocs_gen_files.Nav()
for path in sorted(Path("").rglob("*.md")):
    module_path = path.relative_to("").with_suffix("")
    doc_path = path.relative_to("").with_suffix(".md")
    full_doc_path = Path("readme", doc_path)

    parts = list(module_path.parts)
    if any(part.startswith(".") for part in parts):
        continue
    if any(part.startswith("env") for part in parts):
        continue

    nav2[parts] = doc_path.as_posix()

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        shutil.copy2(path, fd.name)
    mkdocs_gen_files.set_edit_path(full_doc_path, path)

with mkdocs_gen_files.open("readme/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav2.build_literate_nav())
