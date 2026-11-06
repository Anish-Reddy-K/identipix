<p align="center">
  <a href="https://github.com/Anish-Reddy-K/identipix">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="app/static/brand/logo-white.png">
      <img src="app/static/brand/logo.png" alt="Identipix" width="300">
    </picture>
  </a>
</p>

<h3 align="center">Photos that find you.</h3>

<p align="center">
  Guests take a selfie and see only the event photos they appear in.<br>
  Free at <b>identipix.com</b>. Open source.
</p>

<p align="center">
  <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-D81B60"></a>
  <a href="https://github.com/Anish-Reddy-K/identipix/stargazers"><img alt="GitHub stars" src="https://img.shields.io/github/stars/Anish-Reddy-K/identipix?style=flat&color=8E24AA"></a>
  <img alt="Selfies never stored" src="https://img.shields.io/badge/selfies-never%20stored-D81B60">
</p>

<p align="center">
  <a href="https://identipix.com"><img alt="Try it free at identipix.com" src="https://img.shields.io/badge/Try%20it%20free-identipix.com-D81B60?style=for-the-badge"></a>
</p>

<!-- Demo video goes here -->

## How it works

1. Paste a public Google Drive folder at [identipix.com](https://identipix.com). Get an event link and QR code.
2. Guests scan it and take a selfie. No app, no sign-up.
3. They see only their photos, open them in Drive, or save them to their phone.

## Privacy

- Guests agree to face matching first. Selfies are matched in memory and never saved.
- Photos stay in your Drive. Only face fingerprints (numbers, not images) are stored.
- Events are deleted after 30 days, or any time by the organizer.
- No accounts, cookies or analytics.

[Privacy Policy](legal/PRIVACY.md) · [Terms](legal/TERMS.md)

## Develop

Python 3.12, FastAPI, OpenCV, SQLite, plain HTML/CSS/JS.

```
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python fastapi "uvicorn[standard]" opencv-python-headless numpy httpx python-multipart segno pytest
.venv/bin/python -m pytest
```

<details>
<summary>Run your own copy</summary>

Identipix is open source, so you can host it yourself. You need Docker, a Google API key (Drive API enabled) and a Cloudflare tunnel (camera access needs HTTPS).

```
cp .env.example .env     # add GOOGLE_API_KEY, PUBLIC_BASE_URL, TUNNEL_TOKEN
docker compose up -d --build
```

</details>

Matching is not perfect: look-alikes can show up under "Might be you". Tune thresholds in `.env` and measure with `eval/eval.py`.

## Credits

Built with [Claude](https://github.com/claude). Models: YuNet and SFace (OpenCV Zoo). Fonts: Bricolage Grotesque, Inter. Styling: [Neumorphism UI](https://github.com/themesberg/neumorphism-ui-bootstrap) (MIT).

MIT licensed. Made with love in Waterloo, Canada.
