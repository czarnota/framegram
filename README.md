![framegram logo](logo.svg?raw=true)

<p align="center">
  <code>framegram</code> generates cool network packet structure diagrams </br>
    <b>with ease</b>
</p>

# Instalation
tbd

# Usage

`framegram` uses `*.json` to specify the structure of the network packet, that
will be shown on a diagram

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

![frame](tests/example_diagram2.png?raw=true)
