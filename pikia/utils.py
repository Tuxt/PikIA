import os

def sanitize_path(path: str, additional_subdir: str = "") -> str:
    """
    Sanitizes a given path by converting it to an absolute path.
    If the path is empty, it defaults to the current working directory.
    Optionally appends a suffix to the sanitized path.
    """
    # NOTES:
    # - `os.path.abspath("C:")` resolves to the current working directory (`os.getcwd()`)
    #   instead of "C:\\". Adding `os.path.sep` ensures it resolves correctly.
    if len(path) == 2 and path[1] == ':':
        path += os.path.sep
    
    sanitized = os.path.abspath(path)
    return os.path.join(sanitized, additional_subdir) if additional_subdir  else sanitized

