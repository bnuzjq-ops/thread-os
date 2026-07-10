"""CLI entrypoint for the project contract summary."""

from .contract import render_project_summary


def main() -> None:
    print(render_project_summary())


if __name__ == "__main__":
    main()
