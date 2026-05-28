import ast
import os


def check_functions(directory):
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                with open(path, encoding="utf-8") as fd:
                    try:
                        tree = ast.parse(fd.read())
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                                lines = (node.end_lineno or node.lineno) - node.lineno
                                if lines > 60:  # Threshold 60 to be safe
                                    print(f"{path}:{node.lineno} {node.name} ({lines} lines)")  # noqa  # noqa
                    except Exception as e:
                        print(f"Error parsing {path}: {e}")  # noqa  # noqa

if __name__ == "__main__":
    check_functions("src")
