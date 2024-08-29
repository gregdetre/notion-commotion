import json
import os


Posts = dict[str, dict]


def extract_posts(tree, verbose: int = 0):
    root = tree.getroot()

    # Define the namespace
    namespace = {"wp": "http://wordpress.org/export/1.2/"}
    ns = {
        "wp": "http://wordpress.org/export/1.2/",
        "content": "http://purl.org/rss/1.0/modules/content/",
        "dc": "http://purl.org/dc/elements/1.1/",
        "excerpt": "http://wordpress.org/export/1.2/excerpt/",
    }

    # Find all item elements
    items = root.findall(".//item", namespaces=namespace)

    content_dict = {}
    for item in items:
        post_id = item.find("wp:post_id", namespaces=namespace).text

        # Extract content and metadata
        title = item.find("title").text
        content = item.find("{http://purl.org/rss/1.0/modules/content/}encoded").text
        post_date = item.find("wp:post_date_gmt", namespaces=namespace).text
        post_type = item.find("wp:post_type", namespaces=namespace).text
        slug = item.find("wp:post_name", namespaces=namespace).text
        status = item.find("wp:status", namespaces=namespace).text
        post_modified = item.find("wp:post_modified", namespaces=namespace).text
        excerpt = item.find("{http://wordpress.org/export/1.2/excerpt/}encoded").text
        # excerpt = item.find("excerpt:encoded", ns).text  # Extract the excerpt
        # excerpt = item.find("excerpt:encoded").text  # Extract the excerpt

        if post_type == "attachment":
            continue

        # Extract categories and tags
        categories = [cat.text for cat in item.findall('category[@domain="category"]')]
        tags = [tag.text for tag in item.findall('category[@domain="post_tag"]')]

        # Create a dictionary for this post/page
        post_dict = {
            "title": title,
            "content": content,
            "post_date": post_date,
            "post_type": post_type,
            "status": status,
            "post_modified": post_modified,
            "excerpt": excerpt,
            "slug": slug,
            "categories": categories,
            "tags": tags,
        }

        content_dict[post_id] = post_dict

    if verbose > 0:
        display_posts(content_dict)

    return content_dict


def display_posts(posts: Posts):
    # Print a summary of the extracted content
    for post_id, post_data in posts.items():
        # pprint(post_data)
        content = post_data["content"][:100] if post_data["content"] else ""
        print(f"Post ID: {post_id}")
        print(f"Title: {post_data['title']}")
        print(f"Content: {content[:100]}...")
        print(f"Type: {post_data['post_type']}")
        print(f"Date: {post_data['post_date']}")
        print(f"Categories: {', '.join(post_data['categories'])}")
        print(f"Tags: {', '.join(post_data['tags'])}")
        for field in post_data.keys():
            if field in [
                "title",
                "content",
                "post_date",
                "post_type",
                "categories",
                "tags",
            ]:
                continue
            print(f"{field}: {post_data[field]}")
        print("---")


def write_posts(posts: Posts, dirn: str):
    html_filens, json_filens = [], []
    for post_id, post_data in posts.items():
        title = post_data["title"]
        content = post_data["content"]
        if not content or not title:
            print(f"Skipping '{title}' because it has no content")
            continue
        title = title.replace("/", "_")
        html_filen = os.path.join(dirn, f"{title}.html")
        open(html_filen, "w").write(content)
        json_filen = os.path.join(dirn, f"{title}.json")
        json.dump(post_data, open(json_filen, "w"))
        html_filens.append(html_filen)
        json_filens.append(json_filen)
    return html_filens, json_filens
