from typing import Literal, Optional
from md2notionpage.core import parse_md
from notion_client import Client
from urllib.parse import urlparse


# from _secrets import NOTION_API_KEY
# notion = Client(auth=NOTION_API_KEY)


def get_id_from_url(url: str):
    # Parse the URL to remove any # fragment
    parsed_url = urlparse(url)
    # Reconstruct the URL without the fragment and without the `?v=...` query parameter
    clean_url = parsed_url._replace(fragment="")._replace(query="").geturl()

    # e.g. https://www.notion.so/Hello-5ebcf8c341784912bf1103c72d3f36c9 -> Hello-5ebcf8c341784912bf1103c72d3f36c9
    page_slug_and_id = clean_url.split("/")[-1]
    # e.g. Hello-5ebcf8c341784912bf1103c72d3f36c9 -> 5ebcf8c341784912bf1103c72d3f36c9
    page_id = page_slug_and_id.split("-")[-1]
    # page_slug = '-'.join(page_slug_and_id.split('-')[:-1])
    return page_id


def get_blocks(notion: Client, page_id: str, verbose: int = 0):
    # blocks1 = notion.blocks.children.list(block_id=page_id).get("results")
    # last_block_id = blocks1[-1]["id"]
    # blocks2 = notion.blocks.children.list(block_id=page_id, start_cursor=last_block_id).get("results")
    # len(blocks2)
    start_cursor_id = None
    blocks = []
    # see 'has_more' trick below instead
    while True:
        if verbose >= 1:
            print(f"{start_cursor_id=}, {len(blocks)=}")
        if start_cursor_id is None:
            # for some reason, feeding this in as a None argument doesn't work
            new_blocks = notion.blocks.children.list(block_id=page_id).get("results")
        else:
            new_blocks = notion.blocks.children.list(
                block_id=page_id, start_cursor=start_cursor_id
            ).get("results")
        new_blocks = [new_block for new_block in new_blocks if new_block not in blocks]
        if new_blocks and new_blocks[-1]["id"] != start_cursor_id:
            # if new_blocks and blocks[-1]["id"] != start_cursor_id:
            # i haven't figured out a better way of checking if there are more blocks to fetch
            blocks.extend(new_blocks)
            start_cursor_id = blocks[-1]["id"]
        else:
            break
    return blocks


def get_child_pages(notion: Client, page_id: str):
    # {"page_id": "page_title",}
    blocks = get_blocks(notion, page_id)
    child_page_blocks = [block for block in blocks if block["type"] == "child_page"]
    title_from_id = {cpb["id"]: cpb["child_page"]["title"] for cpb in child_page_blocks}
    assert len(set(title_from_id.keys())) == len(
        set(title_from_id.values())
    ), "Some titles appear more than once"
    # titles = title_from_id.values()
    # from collections import Counter
    # print(Counter(titles).most_common())
    return title_from_id


def get_database_pages(notion: Client, database_id: str):
    # https://gemini.google.com/app/c1a1af320de3e731
    database_id = get_id_from_url(database_id)
    results = notion.databases.query(
        database_id=database_id,
    )
    all_pages = results["results"]
    # If the database has more than 100 pages, you'll need to handle pagination
    while results["has_more"]:
        results = notion.databases.query(
            database_id=database_id,
            start_cursor=results["next_cursor"],
        )
        all_pages.extend(results["results"])
    return all_pages


def create_notion_page(
    notion: Client,
    parent_page_id: str,
    title: str,
    properties: dict[str, str],
    typ: Literal["page", "database"],
    children_blocks: Optional[list[dict[str, str]]] = None,
    verbose: int = 0,
):
    """
    e.g.

    properties = {
        "Name": {"title": [{"text": {"content": "My New Database Entry"}}]},
        "Tags": {"multi_select": [{"name": "Tag1"}, {"name": "Tag2"}]},
        "Published": {"date": {"start": "2021-01-01"}},
    }

    children_blocks =
    [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "This is a new page created using the Notion API."
                            },
                        }
                    ]
                },
            }
        ],
    """

    # https://claude.ai/chat/c14a3432-5030-4cef-8dc4-e85fbd54a81a

    # Specify the parent page or database where you want to create the new page
    id_typ = {"page": "page_id", "database": "database_id"}[typ]
    parent = {
        # "type": "page_id",
        id_typ: parent_page_id,
    }

    # Define the properties for the new page
    properties = {"title": [{"text": {"content": title}}]}

    new_page = notion.pages.create(
        parent=parent, properties=properties, children=children_blocks
    )

    if verbose > 0:
        print(f"New page created with ID: {new_page['id']}")
    return new_page


def update_page(
    notion: Client,
    page_id: str,
    properties: dict[str, str],
    blocks: Optional[list[dict[str, str]]],
    verbose: int = 0,
):
    updated_page = notion.pages.update(page_id=page_id, properties=properties)

    if blocks is not None:
        # Get all the existing blocks on the page
        old_blocks = notion.blocks.children.list(block_id=page_id).get("results")

        # Delete all existing blocks
        for block in old_blocks:
            notion.blocks.delete(block_id=block["id"])

        # Update the page content
        notion.blocks.children.append(
            block_id=page_id,
            children=blocks,
        )

    if verbose > 0:
        print(f"Page updated successfully. Updated page ID: {updated_page['id']}")

    return updated_page


def notion_blocks_from_markdown(md_txt: str):
    # probably not necessary any more, because I'm just going to import the html directly in Notion
    converted_blocks = parse_md(md_txt)
    return converted_blocks

    # import mistletoe
    # from md2notion.NotionPyRenderer import NotionPyRenderer

    # # https://github.com/markomanninen/md2notion

    # # converted_blocks = mistletoe.markdown(md_txt, NotionPyRenderer)
    # converted_html = mistletoe.markdown(md_txt)
    # print(converted_html)
