import pytest

from docs_transduction_study import locators
from docs_transduction_study.stages import a3_extract

MDX = """---
title: Example page
---
import { Steps } from '@astrojs/starlight/components';

## Configure the project

Update `astro.config.mjs`. Then read the [configuration guide](/en/reference/configuration/) -- it's short.

:::caution[Before you start]
You **must** install the adapter first.
:::

<Steps>
1. Install the package.

   ```sh
   npm install example
   ```

2. Restart the "dev" server...
</Steps>
"""

# Shaped like Starlight output: heading anchor label, smartypants, aside title,
# Expressive Code frame label, and inline elements extracted with separators.
HTML = """<html><body><div class="sl-markdown-content">
<div class="sl-heading-wrapper level-h2"><h2 id="configure-the-project">Configure the project</h2>
<a class="sl-anchor-link" href="#configure-the-project"><span class="sr-only">Section titled “Configure the project”</span></a></div>
<p>Update <code>astro.config.mjs</code>. Then read the <a href="/en/reference/configuration/">configuration guide</a> – it’s short.</p>
<aside class="starlight-aside"><p class="starlight-aside__title">Before you start</p>
<div class="starlight-aside__content"><p>You <strong>must</strong> install the adapter first.</p></div></aside>
<div class="sl-steps"><ol><li><p>Install the package.</p>
<div class="expressive-code"><figure><figcaption><span class="title"></span><span class="sr-only">Terminal window</span></figcaption>
<pre><code>npm install example</code></pre></figure></div></li>
<li><p>Restart the “dev” server…</p></li></ol></div>
</div></body></html>"""


@pytest.fixture
def rendered(tmp_path):
    page = tmp_path / "index.html"
    page.write_text(HTML, encoding="utf-8")
    return a3_extract.extract_article_text(page)[0]


def test_fold_maps_back_to_original_coordinates():
    folded, positions = locators.fold("A “B” -- c…")
    assert folded == 'a"b"-c...'
    assert positions[-1] == positions[-3] == len("A “B” -- c")


@pytest.mark.parametrize(
    "host",
    [
        "Update `astro.config.mjs`. Then read the [configuration guide](/en/reference/configuration/) -- it's short.",
        "You **must** install the adapter first.",
        "## Configure the project\n\nUpdate `astro.config.mjs`. Then read",
        ":::caution[Before you start]\nYou **must** install the adapter first.\n:::",
        (
            "Update `astro.config.mjs`. Then read the [configuration guide](/en/reference/configuration/) -- it's short.\n\n"
            ":::caution[Before you start]\nYou **must** install the adapter first."
        ),
        'Install the package.\n\n   ```sh\n   npm install example\n   ```\n\n2. Restart the "dev" server...',
    ],
)
def test_hosts_resolve_once_in_extracted_text(rendered, host):
    assert host in MDX
    start, end = locators.resolve_host(host, MDX, rendered)
    folded_rendered, _ = locators.fold(rendered[start:end])
    start_locator, end_locator = locators.locators(host, MDX)
    assert folded_rendered.startswith(start_locator)
    assert folded_rendered.endswith(end_locator)


def test_anchor_must_be_unique_inside_host(rendered):
    host = "You **must** install the adapter first."
    span = locators.resolve_host(host, MDX, rendered)
    anchor = locators.resolve_anchor("install the adapter", rendered, span)
    assert rendered[anchor[0] : anchor[1]] == "install the adapter"
    with pytest.raises(ValueError, match="exactly once"):
        locators.resolve_anchor("Install the package", rendered, span)


def test_resolution_fails_closed(rendered):
    with pytest.raises(ValueError, match="too short"):
        locators.locators("Short.", MDX)
    with pytest.raises(ValueError, match="no unique locator"):
        locators.locators(
            "Install the package.\n\n   ```sh\n   npm install example\n   ```",
            MDX + "\nInstall the package. Elsewhere.\n",
        )
    with pytest.raises(ValueError, match="times in its A0 page"):
        locators.locators(
            "You **must** install the adapter first.",
            MDX + "\nYou must install the adapter first.\n",
        )
    with pytest.raises(ValueError, match="exactly once"):
        locators.resolve_host(
            "You **must** install the adapter first.", MDX, rendered + rendered
        )
    with pytest.raises(ValueError, match="exactly once"):
        locators.resolve_host(
            "You **must** install the adapter first.", MDX, "unrelated"
        )


@pytest.mark.parametrize(
    "host",
    [
        "<Steps>\n1. Install the package.",
        "Install the package.\n```sh",
        "| a | b |\nText",
    ],
)
def test_hosts_must_begin_and_end_in_prose(host):
    with pytest.raises(ValueError, match="markup"):
        locators.check_edges(host)


def test_projection_renders_default_aside_titles_and_drops_syntax():
    projected = locators.project_mdx(
        ":::tip\nUse [it](/x) <Badge text='x' />.\n:::\n| a | b |\n|---|---|\n"
    )
    assert "Tip" in projected and "(/x)" not in projected and "Badge" not in projected
    assert "---" not in projected


def test_code_content_is_not_treated_as_markup():
    projected = locators.project_mdx(
        "## `files`\n\nUse `<html>` here.\n\n```jsx\n<Layout>{children}</Layout>\n```\n"
    )
    assert 'files Section titled "files"' in projected
    assert "<html>" in projected and "<Layout>{children}</Layout>" in projected
