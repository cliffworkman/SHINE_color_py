"""Build, serve, or export local Phase 1 review projects."""

import argparse
import threading
import webbrowser
from .project import compare_batch, open_report
from .server import ReviewServer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser(
        "build", help="Compare a completed normalization batch; never normalize"
    )
    build.add_argument("--inputs", required=True)
    build.add_argument("--outputs", required=True)
    build.add_argument("--manifest", required=True)
    build.add_argument("--review-dir", required=True)
    serve = commands.add_parser(
        "serve", help="Open the local reviewer; Ctrl+C stops it"
    )
    serve.add_argument("project")
    serve.add_argument("--port", type=int, default=0)
    serve.add_argument("--no-browser", action="store_true")
    export = commands.add_parser("export", help="Create a new portable snapshot ZIP")
    export.add_argument("project")
    export.add_argument("destination")
    export.add_argument("--include-images", action="store_true")
    args = parser.parse_args()
    if args.command == "build":
        report = compare_batch(
            args.inputs,
            args.outputs,
            manifest=args.manifest,
            review_dir=args.review_dir,
            progress=lambda i, n: print(f"Analyzed {i}/{n}", flush=True),
        )
        print(report.root)
    elif args.command == "export":
        print(open_report(args.project).export(args.destination, args.include_images))
    else:
        server = ReviewServer(args.project, args.port)
        print(
            f"{server.url}\nLocal only. Decisions save to disk. Ctrl+C to stop.",
            flush=True,
        )
        if not args.no_browser:
            webbrowser.open(server.url)
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
        finally:
            server.close()


if __name__ == "__main__":
    main()
