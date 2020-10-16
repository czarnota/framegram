![framegram logo](logo.svg?raw=true)

<p align="center">
  <code>framegram</code> generates cool network packet structure diagrams </br>
    <b>with ease</b>
</p>

# Installation

You can install `framegram` by running
```console
$ python setup.py install
```

This will make the `framegram` script available to you

```console
$ framegram --help
```

# Usage

`framegram` uses `*.json` to specify the structure of the network packet, that
will be presented.

```json
[
{
    "name": "Ethernet Frame",
    "_": [
        { "name": "Destination MAC", "_": 48, "val": ["DE", "AD", "BE", "EF", "CC", "DD"] },
        { "name": "Source MAC", "_": 48, "val": ["DE", "AD", "BE", "EF", "CC", "DD"] },
        { "name": "802.1Q Header", "_": [
            { "name": "TPID", "_": 16, "val": [ "0x8100" ] },
            { "name": "TCI", "_": 16, "val": [ "..." ] }
        ]},
        { "name": "Ethertype", "_": 16, "val": ["0x8000"] }
    ]
}
]
```

Then you can run framegram to generate packet diagram

```console
$ framegram --width 1440 --height 200 example_diagram2.json
```

And this is the result

![frame](tests/example_diagram2.png?raw=true)

Available options
```
$ framegram --help
usage: framegram [-w WIDTH] [-h HEIGHT] [--wrap WRAP] [--help] file

positional arguments:
  file                  The file to render diagram from

optional arguments:
  -w WIDTH, --width WIDTH
                        Output width
  -h HEIGHT, --height HEIGHT
                        Output image height
  --wrap WRAP           Wrap
  --help                Print help
```

# License

`framegram` is licensed under MIT, which means you can do anything you want
with it as long as you include the copyright notice. See [LICENSE](LICENSE)
for details.
