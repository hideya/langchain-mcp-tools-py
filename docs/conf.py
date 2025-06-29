# At the top of your conf.py file
import os
import sys
from unittest.mock import MagicMock

# Add both source directory and docs directory to path
sys.path.insert(0, os.path.abspath('../src'))
sys.path.insert(0, os.path.abspath('.'))

# Try to get version from package
try:
    from langchain_mcp_tools import __version__
    version = __version__
    release = __version__
except ImportError:
    # Fallback to manual version if import fails during doc build
    version = 'unknown'
    release = 'unknown'

# Set environment variable for documentation build
os.environ['SPHINX_BUILD'] = 'True'

# Mock all problematic imports
autodoc_mock_imports = [
    'anyio', 'jsonschema_pydantic', 'langchain_core', 
    'mcp', 'pydantic', 'mcp.types'
]

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'langchain-mcp-tools-py'
copyright = '2025, hideya'
author = 'hideya'

# Version info (dynamically loaded from package above)
# version and release are set from package import or fallback

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

# Add to your extensions list
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx_autodoc_typehints',
]

# Configure Napoleon for Google-style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = False

# Configure autodoc
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']

# Alabaster theme options (to show version prominently)
html_theme_options = {
    'description': f'MCP Tools for LangChain v{release}',
    'github_user': 'hideya',  # Replace with your GitHub username if public
    'github_repo': 'langchain-mcp-tools-py',  # Replace with your repo name if public
    'show_powered_by': False,
    'sidebar_width': '230px',
    'page_width': '1024px',
    'fixed_sidebar': True,
}

# Show version in the HTML title
html_title = f'{project} v{release} Documentation'

# Show version info in sidebar
html_short_title = f'{project} v{release}'

# Add version info to the page footer
html_last_updated_fmt = '%b %d, %Y'
html_show_sphinx = False

# Enable RST substitutions for version info
rst_epilog = f"""
.. |release| replace:: {release}
.. |version| replace:: {version}
"""
