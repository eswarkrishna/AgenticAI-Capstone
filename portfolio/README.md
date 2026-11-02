# Neo — portfolio (static)

Single-page portfolio for **Neo** (`Neoistheone` on GitHub). No build step required.

## View locally

From the repository root:

```bash
# Python 3
python3 -m http.server 8080 --directory portfolio

# Or open the file directly (some browsers restrict local fonts; a local server is preferred)
xdg-open portfolio/index.html
```

Then visit [http://localhost:8080](http://localhost:8080).

## Customize

Edit `index.html` placeholders (hero line, work cards, about copy, email, social links). Styles live in `css/styles.css`; scroll/spy behavior in `js/main.js`.

This folder is independent of the Resume Screening Agent Streamlit app in `app/`.
