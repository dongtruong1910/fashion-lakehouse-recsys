import os
import re
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def get_all_markdown_files():
    md_files = []
    for root, dirs, files in os.walk(REPO_ROOT):
        if ".git" in root or ".venv" in root:
            continue
        for f in files:
            if f.endswith(".md"):
                md_files.append(os.path.join(root, f))
    return sorted(md_files)


def test_no_file_uri_in_markdown():
    """Ensure no markdown file contains absolute file:/// URLs in markdown links."""
    violations = []
    file_uri_pattern = re.compile(r"\(file:///[^)]*\)")
    for md_file in get_all_markdown_files():
        rel_path = os.path.relpath(md_file, REPO_ROOT).replace("\\", "/")
        with open(md_file, "r", encoding="utf-8") as fh:
            content = fh.read()
        if file_uri_pattern.search(content):
            violations.append(rel_path)
    assert not violations, f"The following files contain file:/// links: {violations}"
    print(f"PASS: No 'file:///' link URLs in any markdown files ({len(get_all_markdown_files())} files checked).")


def test_all_relative_links_resolve():
    """Verify that every relative markdown link resolves to an existing file or directory."""
    broken_links = []
    total_checked = 0

    for md_file in get_all_markdown_files():
        rel_source = os.path.relpath(md_file, REPO_ROOT).replace("\\", "/")
        source_dir = os.path.dirname(md_file)
        with open(md_file, "r", encoding="utf-8") as fh:
            content = fh.read()

        matches = LINK_PATTERN.findall(content)
        for text, target in matches:
            # Skip external URLs, mailto, and in-page anchor links
            if (
                target.startswith("http://")
                or target.startswith("https://")
                or target.startswith("mailto:")
                or target.startswith("#")
            ):
                continue

            total_checked += 1
            clean_target = target.split("#")[0]
            if not clean_target:
                continue

            # Must not use Windows backslashes in markdown URLs
            if "\\" in clean_target:
                broken_links.append({
                    "file": rel_source,
                    "text": text,
                    "target": target,
                    "reason": "Uses backslash '\\' instead of forward slash '/'",
                })
                continue

            resolved_path = os.path.normpath(os.path.join(source_dir, clean_target))
            if not os.path.exists(resolved_path):
                broken_links.append({
                    "file": rel_source,
                    "text": text,
                    "target": target,
                    "resolved": resolved_path,
                    "reason": "Target path does not exist on disk",
                })
            else:
                rel_dest = os.path.relpath(resolved_path, REPO_ROOT).replace("\\", "/")
                print(f"  [OK] {rel_source} -> [{text}]({target}) resolves to {rel_dest}")

    assert total_checked > 0, "No relative links were found to test."
    assert not broken_links, f"Found {len(broken_links)} broken relative links: {broken_links}"
    print(f"PASS: All {total_checked} relative markdown links successfully resolve to existing files/folders!")


if __name__ == "__main__":
    try:
        test_no_file_uri_in_markdown()
        test_all_relative_links_resolve()
        print("\n=== ALL MARKDOWN LINK TESTS PASSED! ===")
        sys.exit(0)
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}", file=sys.stderr)
        sys.exit(1)
