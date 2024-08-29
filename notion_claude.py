from IPython.display import display
import json
from notion_client import Client
import os
from pprint import pprint
import sys
from typing import Any


def list_item_to_html(block: dict[str, Any], block_id: str, list_type: str) -> str:
    content = rich_text_to_html(block[block["type"]]["rich_text"])
    return f'<li data-block-id="{block_id}">{content}</li>'


def todo_to_html(block: dict[str, Any], block_id: str) -> str:
    content = rich_text_to_html(block["to_do"]["rich_text"])
    checked = "checked" if block["to_do"]["checked"] else ""
    return f'<div data-block-id="{block_id}"><input type="checkbox" {checked} disabled> {content}</div>'


def toggle_to_html(block: dict[str, Any], block_id: str) -> str:
    content = rich_text_to_html(block["toggle"]["rich_text"])
    return f'<details data-block-id="{block_id}"><summary>{content}</summary></details>'


def image_to_html(block: dict[str, Any], block_id: str) -> str:
    image_type = block["image"]["type"]
    if image_type == "external":
        url = block["image"]["external"]["url"]
    elif image_type == "file":
        url = block["image"]["file"]["url"]
    else:
        url = "#"
    caption = rich_text_to_html(block["image"].get("caption", []))
    return f'<figure data-block-id="{block_id}"><img src="{url}" alt="{caption}"><figcaption>{caption}</figcaption></figure>'


def code_to_html(block: dict[str, Any], block_id: str) -> str:
    code = block["code"]["rich_text"][0]["plain_text"]
    language = block["code"]["language"]
    return f'<pre data-block-id="{block_id}"><code class="language-{language}">{code}</code></pre>'


def quote_to_html(block: dict[str, Any], block_id: str) -> str:
    content = rich_text_to_html(block["quote"]["rich_text"])
    return f'<blockquote data-block-id="{block_id}">{content}</blockquote>'


def process_notion_page(notion: Client, page_id: str, output_dir: str = "."):
    blocks = notion.blocks.children.list(block_id=page_id).get("results")

    # Get page title
    page = notion.pages.retrieve(page_id=page_id)
    page_title = get_page_title(page["properties"])

    # Generate HTML content
    html_output = f"<h1>{page_title}</h1>\n" + notion_to_html(
        blocks, notion, output_dir
    )

    # Write main page HTML to file
    safe_title = get_safe_filename(page_title)
    output_file = os.path.join(output_dir, f"{safe_title}_{page_id}.html")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(
            f"""<!DOCTYPE html>
<html>
<head>
    <title>{page_title}</title>
</head>
<body>
    {html_output}
</body>
</html>"""
        )

    print(f"Generated {output_file}")


def paragraph_to_html(block: dict[str, Any], block_id: str) -> str:
    content = rich_text_to_html(block["paragraph"]["rich_text"])
    return f'<p data-block-id="{block_id}">{content}</p>'


def bulleted_list_item_to_html(block: dict[str, Any], block_id: str) -> str:
    content = rich_text_to_html(block["bulleted_list_item"]["rich_text"])
    return f'<ul><li data-block-id="{block_id}">{content}</li></ul>'


def child_page_to_html(block: dict[str, Any], block_id: str, output_dir: str) -> str:
    title = block["child_page"]["title"]
    filename = f"{get_safe_filename(title)}_{block_id}.html"
    return f'<div data-block-id="{block_id}"><h3>Child Page: <a href="{filename}">{title}</a></h3></div>'


def table_of_contents_to_html(block: dict[str, Any], block_id: str) -> str:
    return f'<div data-block-id="{block_id}"><nav><h4>Table of Contents</h4><ul id="table-of-contents"></ul></nav></div>'


def get_blocks(notion: Client, page_id: str) -> list[dict[str, Any]]:
    all_blocks = []
    start_cursor = None

    while True:
        response = notion.blocks.children.list(
            block_id=page_id,
            start_cursor=start_cursor,
            page_size=100,  # You can adjust this value
        )

        blocks = response["results"]
        all_blocks.extend(blocks)

        if not response["has_more"]:
            break

        start_cursor = response["next_cursor"]

    return all_blocks


def get_page_title(page: dict[str, Any]) -> str:
    if "properties" in page:
        for prop in page["properties"].values():
            if prop["type"] == "title" and prop["title"]:
                return prop["title"][0]["plain_text"]
    elif "child_page" in page:
        return page["child_page"]["title"]
    return "Untitled"


def get_safe_filename(title: str) -> str:
    return (
        "".join([c for c in title if c.isalnum() or c in (" ", "-", "_")])
        .rstrip()
        .replace(" ", "_")
    )


def divider_to_html(block: dict[str, Any], block_id: str) -> str:
    return f'<hr data-block-id="{block_id}">'


def process_database(notion: Client, database_id: str, output_dir: str):
    database = notion.databases.retrieve(database_id)
    database_title = (
        database["title"][0]["plain_text"] if database["title"] else "Untitled Database"
    )

    print(f"Processing database: {database_title}")

    # Query all items in the database with pagination
    start_cursor = None
    while True:
        response = notion.databases.query(
            database_id=database_id,
            start_cursor=start_cursor,
            page_size=100,  # You can adjust this value
        )
        results = response["results"]

        for item in results:
            item_id = item["id"]
            item_title = get_page_title(item)
            print(f"Processing database item: {item_title}")

            # Extract database properties
            database_properties = {}
            for prop_name, prop_data in item["properties"].items():
                prop_type = prop_data["type"]
                if prop_type == "rich_text":
                    prop_value = " ".join(
                        [text["plain_text"] for text in prop_data["rich_text"]]
                    )
                elif prop_type == "title":
                    prop_value = " ".join(
                        [text["plain_text"] for text in prop_data["title"]]
                    )
                elif prop_type == "select":
                    prop_value = (
                        prop_data["select"]["name"] if prop_data["select"] else ""
                    )
                elif prop_type == "multi_select":
                    prop_value = ", ".join(
                        [select["name"] for select in prop_data["multi_select"]]
                    )
                elif prop_type == "date":
                    prop_value = prop_data["date"]["start"] if prop_data["date"] else ""
                elif prop_type == "checkbox":
                    prop_value = "Yes" if prop_data["checkbox"] else "No"
                else:
                    prop_value = str(prop_data.get(prop_type, ""))

                database_properties[prop_name] = prop_value

            # Process each database item as a page
            process_page_recursively(notion, item_id, output_dir, database_properties)

        if not response.get("has_more", False):
            break

        start_cursor = response.get("next_cursor")


def notion_to_html(
    blocks: list[dict[str, Any]], notion: Client, output_dir: str, page_id: str
) -> str:
    html = []

    for block in blocks:
        block_id = block["id"]
        block_type = block["type"]

        if block_type == "paragraph":
            html.append(paragraph_to_html(block, block_id))
        elif block_type.startswith("heading_"):
            html.append(heading_to_html(block, block_id))
        elif block_type == "bulleted_list_item":
            html.append(list_item_to_html(block, block_id, "ul"))
        elif block_type == "numbered_list_item":
            html.append(list_item_to_html(block, block_id, "ol"))
        elif block_type == "to_do":
            html.append(todo_to_html(block, block_id))
        elif block_type == "toggle":
            html.append(toggle_to_html(block, block_id))
        elif block_type == "child_page":
            html.append(child_page_to_html(block, block_id, output_dir))
        elif block_type == "image":
            html.append(image_to_html(block, block_id))
        elif block_type == "code":
            html.append(code_to_html(block, block_id))
        elif block_type == "quote":
            html.append(quote_to_html(block, block_id))
        elif block_type == "divider":
            html.append(divider_to_html(block, block_id))
        elif block_type == "child_database":
            html.append(child_database_to_html(block, block_id, notion, output_dir))
        elif block_type == "table_of_contents":
            html.append(table_of_contents_to_html(block, block_id))
        else:
            html.append(
                f'<div data-block-id="{block_id}">Unsupported block type: {block_type}</div>'
            )

    return "\n".join(html)


def heading_to_html(block: dict[str, Any], block_id: str) -> str:
    heading_level = int(block["type"][-1])
    content = rich_text_to_html(block[block["type"]]["rich_text"])
    anchor = f"heading-{block_id}"
    return f'<h{heading_level} id="{anchor}" data-block-id="{block_id}">{content}</h{heading_level}>'


def rich_text_to_html(rich_text: list[dict[str, Any]]) -> str:
    html = []
    for text in rich_text:
        content = text["plain_text"]
        link = text.get("href")
        annotations = text["annotations"]

        if annotations["bold"]:
            content = f"<strong>{content}</strong>"
        if annotations["italic"]:
            content = f"<em>{content}</em>"
        if annotations["strikethrough"]:
            content = f"<del>{content}</del>"
        if annotations["underline"]:
            content = f"<u>{content}</u>"
        if annotations["code"]:
            content = f"<code>{content}</code>"

        if link:
            if link.startswith("/"):
                # Internal link to another page
                page_id = link.split("/")[-1]
                content = f'<a href="{get_safe_filename(content)}_{page_id}.html">{content}</a>'
            elif link.startswith("#"):
                # Anchor link within the same page
                block_id = link[1:]
                content = f'<a href="#heading-{block_id}">{content}</a>'
            else:
                # External link
                content = f'<a href="{link}">{content}</a>'

        html.append(content)

    return "".join(html)


def child_database_to_html(
    block: dict[str, Any], block_id: str, notion: Client, output_dir: str
) -> str:
    database_id = block["id"]
    database_title = block["child_database"]["title"]

    # Query the database with pagination
    entries_html = []
    start_cursor = None

    while True:
        response = notion.databases.query(
            database_id=database_id,
            start_cursor=start_cursor,
            page_size=100,  # Adjust as needed
        )
        results = response.get("results", [])

        for page in results:
            page_id = page["id"]
            page_title = get_page_title(page)
            safe_title = get_safe_filename(page_title)
            page_url = f"{safe_title}_{page_id}.html"
            entries_html.append(f'<li><a href="{page_url}">{page_title}</a></li>')

            # Generate individual page HTML
            page_blocks = notion.blocks.children.list(block_id=page_id).get("results")
            page_html = notion_to_html(page_blocks, notion, output_dir, page_id)

            # Get database fields
            fields_html = get_database_fields_html(page["properties"])

            # Write individual page HTML to file
            with open(os.path.join(output_dir, page_url), "w", encoding="utf-8") as f:
                f.write(
                    f"""<!DOCTYPE html>
<html>
<head>
    <title>{page_title}</title>
</head>
<body>
    <h1>{page_title}</h1>
    {fields_html}
    {page_html}
</body>
</html>"""
                )

        if not response.get("has_more"):
            break
        start_cursor = response.get("next_cursor")

    # Return HTML for database listing
    return f"""
    <div data-block-id="{block_id}">
        <h2>{database_title}</h2>
        <ul>
            {''.join(entries_html)}
        </ul>
    </div>
    """


def get_database_fields_html(properties: dict[str, Any]) -> str:
    fields_html = ['<div class="database-fields">']
    for prop_name, prop_value in properties.items():
        if (
            prop_name.lower() != "name"
        ):  # Exclude the 'Name' field as it's already used as the title
            field_value = format_property_value(prop_value)
            fields_html.append(f"<p><strong>{prop_name}:</strong> {field_value}</p>")
    fields_html.append("</div>")
    return "\n".join(fields_html)


def format_property_value(prop: dict[str, Any]) -> str:
    prop_type = prop["type"]
    if prop_type == "rich_text":
        return rich_text_to_html(prop["rich_text"])
    elif prop_type == "number":
        return str(prop["number"])
    elif prop_type == "select":
        return prop["select"]["name"] if prop["select"] else ""
    elif prop_type == "multi_select":
        return ", ".join([option["name"] for option in prop["multi_select"]])
    elif prop_type == "date":
        date = prop["date"]
        if date:
            return (
                f"{date['start']} - {date['end']}" if date.get("end") else date["start"]
            )
        return ""
    elif prop_type == "people":
        return ", ".join([person["name"] for person in prop["people"]])
    elif prop_type == "files":
        return ", ".join([file["name"] for file in prop["files"]])
    elif prop_type == "checkbox":
        return "Yes" if prop["checkbox"] else "No"
    elif prop_type == "url":
        return f'<a href="{prop["url"]}">{prop["url"]}</a>' if prop["url"] else ""
    elif prop_type == "email":
        return (
            f'<a href="mailto:{prop["email"]}">{prop["email"]}</a>'
            if prop["email"]
            else ""
        )
    elif prop_type == "phone_number":
        return prop["phone_number"] or ""
    elif prop_type == "formula":
        return str(prop["formula"].get("string", ""))
    else:
        return "Unsupported property type"


def process_page_recursively(notion: Client, page_id: str, output_dir: str):
    blocks = get_blocks(notion, page_id)

    # Get page title
    page = notion.pages.retrieve(page_id)
    title = get_page_title(page)

    # Add title as H1 at the top
    html_content = f"<h1>{title}</h1>\n" + notion_to_html(
        blocks, notion, output_dir, page_id
    )

    # Create a safe filename
    safe_title = get_safe_filename(title)
    filename = f"{safe_title}_{page_id}.html"

    # Write the HTML file
    with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
        f.write(
            f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
</head>
<body>
    {html_content}
</body>
</html>"""
        )

    print(f"Created file: {filename}")

    # Process child pages and databases
    for block in blocks:
        if block["type"] == "child_page":
            child_page_id = block["id"]
            process_page_recursively(notion, child_page_id, output_dir)
        elif block["type"] == "child_database":
            process_database(notion, block["id"], output_dir)
