# PROXIMA (TMDB API client)

`proxima` is a simple client to The Movie DataBase (TMDB) public API with response caching.
The client can be used directly through a command line tool,
or alternatively it can be exposed through an API to be used by a frontend.

## Installation

Using `pip`:

```bash
pip install git+https://github.com/mmarinriera/proxima
```
or, alternatively, add the following line to your `requirements.txt`:

```
git+https://github.com/mmarinriera/proxima
```

Using `uv`:

Install as a third party package to your project:

```bash
uv add git+https://github.com/mmarinriera/proxima
```

Install as a standalone tool:

```bash
uv tool install git+https://github.com/mmarinriera/proxima
```

## Usage

You need to provide a valid TMDB API key through the `TMDB_API_TOKEN` environment variable:

```bash
export TMDB_API_TOKEN=<YOUR_API_KEY>
```

### Command Line Interface

Run `proxima --help` after installation to check the CLI documentation.

#### Example

Use the `discover` command to query the top 5 ranked science fiction movies between 2020 and 2025,
displaying title, release date and average rating,

```bash
proxima discover movie \
--genre "science fiction" \
--from 2020 \
--until 2025 \
--sort-by vote_average \
--n-results 5 \
-o title \
-o release_date \
-o vote_average
```

Result:

```bash
╭─ 1 ─────────────────────────────────────────────────────────────────────────────────────────╮
│  Title:         Spider-Man: Across the Spider-Verse                                         │
│  Release date:  2023-05-31                                                                  │
│  Vote average:  8.35                                                                        │
╰─────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ 2 ─────────────────────────────────────────────────────────────────────────────────────────╮
│  Title:         The Wild Robot                                                              │
│  Release date:  2024-09-12                                                                  │
│  Vote average:  8.308                                                                       │
╰─────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ 3 ─────────────────────────────────────────────────────────────────────────────────────────╮
│  Title:         Evangelion: 3.0+1.0 Thrice Upon a Time                                      │
│  Release date:  2021-03-08                                                                  │
│  Vote average:  8.213                                                                       │
╰─────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ 4 ─────────────────────────────────────────────────────────────────────────────────────────╮
│  Title:         Dune: Part Two                                                              │
│  Release date:  2024-02-27                                                                  │
│  Vote average:  8.136                                                                       │
╰─────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ 5 ─────────────────────────────────────────────────────────────────────────────────────────╮
│  Title:         Uranus 2324                                                                 │
│  Release date:  2024-07-04                                                                  │
│  Vote average:  8.1                                                                         │
╰─────────────────────────────────────────────────────────────────────────────────────────────╯
```

### API

To start the API app from the command line, make sure to activate the virtual environment and run,

```bash
fastapi run src/proxima/app.py
```

or, if using uv, simply run,

```bash
uv run fastapi run src/proxima/app.py
```

#### Docker

You can run the TMDB client API inside a container.
To build the image, move to the project directory and run,

```bash
docker build -t proxima:latest .
```

To run the container,

```bash
docker run \
-d \
--name proxima \
--volume proxima-cache:/app/.cache \
-p <OUT_PORT>:8000 \
-e TMDB_API_TOKEN=<YOUR_API_KEY> \
proxima:latest
```

Make sure to replace `<OUT_PORT>` with the port where you want the API exposed
and `<YOUR_API_KEY>` with your TMDB API key.
