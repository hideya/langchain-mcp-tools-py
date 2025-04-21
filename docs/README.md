# Documentation for langchain-mcp-tools-py

This directory contains the Sphinx documentation setup for the `langchain-mcp-tools-py` project.

## Special Setup Notes

### Documentation-Only Module

The documentation uses a simplified version of the module (`langchain_mcp_tools_docs.py`) instead of the actual implementation. This approach was chosen to avoid issues with:

1. Complex import dependencies
2. Type annotations using the pipe operator (`|`) which can cause problems with Sphinx
3. Module-level code that might exit the process during documentation build

The file `langchain_mcp_tools_docs.py` contains simplified versions of the classes and functions with properly formatted docstrings but without the actual implementation details.

### When to Update the Documentation-Only Module

You should update `langchain_mcp_tools_docs.py` when:

1. You add new public functions or classes to the actual module
2. You change function/method signatures (parameters or return types)
3. You modify docstrings in the original code
4. You make any changes to types or classes that are exposed in the API

### How to Update the Documentation-Only Module

1. Copy the updated docstrings from the main module
2. Keep only the type definitions and function signatures (without implementation)
3. Make sure all docstrings follow Google style formatting
4. Run `make html` to verify that the documentation builds without warnings

## Building the Documentation

To build the documentation:

```bash
# Navigate to the docs directory
cd docs

# Build HTML documentation
make html

# View the documentation
open _build/html/index.html
```

## Documentation Structure

- `conf.py`: Sphinx configuration file
- `index.rst`: Main entry point for the documentation
- `modules/`: Directory containing module-specific documentation
  - `langchain_mcp_tools.rst`: Documentation for the main module
- `langchain_mcp_tools_docs.py`: Documentation-only version of the module
- `_build/`: Generated documentation (not committed to the repository)

## Tips for Docstrings

When writing docstrings, follow these guidelines:

1. Use Google style format (supported by Napoleon extension)
2. Add blank lines after section headers (Args:, Returns:, etc.)
3. Use asterisks (*) for bullet points
4. Add proper indentation for code examples
5. Add blank lines before and after code blocks
6. End all sentences with a period

Example of a well-formatted docstring:

```python
def example_function(arg1: str, arg2: int = 0) -> bool:
    """Short description of the function.
    
    More detailed explanation of what the function does and how to use it.
    
    Args:
        arg1: Description of the first argument
        arg2: Description of the second argument, defaults to 0
    
    Returns:
        Description of the return value
    
    Raises:
        ValueError: When the function encounters an invalid input
    
    Example:
        
        result = example_function("test", 42)
        
        # Use the result
        print(result)
    """
    # Implementation
    pass
```

## Theme Customization

The documentation uses the default Alabaster theme. To customize the theme, 
edit the `html_theme` and related settings in `conf.py`.
