# YouTube Player sidecar

This directory contains the Python sidecar and configuration for playing YouTube videos seamlessly within the CTRL Arcade frontend.

## How to add songs

The media player reads from `playlist.json`. To add new songs or videos to the arcade, follow these steps:

1. Open `playlist.json` in any text editor.
2. The file contains a JSON array of objects.
3. Add a new object for your song. Ensure it matches this format:

```json
{
    "title": "Song Title",
    "artist": "Artist Name",
    "youtube_url": "https://www.youtube.com/watch?v=..."
}
```

Make sure you don't forget the comma `,` between objects if you add multiple items.
When you launch the Media Player from the main menu, it will automatically load the updated playlist.
