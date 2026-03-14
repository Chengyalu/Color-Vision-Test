# Color Vision Tests

A Python toolkit for administering three common color vision tests:

- D15
- FM D-15
- HRR

This project provides a graphical user interface for presenting the tests, collecting participant responses, and exporting results as CSV files.

## Features

- D15 arrangement test
- FM D-15 arrangement test
- HRR symbol and position recall test
- Graphical user interface built with Tkinter
- CSV export for participant responses and test results
- Modular code structure for future extension

## Project Structure

```text
color-vision-tests/
├── README.md
├── .gitignore
├── requirements.txt
├── run.py
├── color_vision_tests/
│   ├── __init__.py
│   ├── assets/
│   │   └── hrr/
│   ├── data/
│   │   ├── d15_colors.json
│   │   ├── fmd15_colors.json
│   │   └── hrr_keys.json
│   ├── io/
│   ├── scoring/
│   ├── tests/
│   └── ui/
└── outputs/
```

## Requirements

- Python 3.10 or later
- pillow
- colour-science

## Installation

Clone the repository and install dependencies:

```bash
pip install -r requirements.txt
```

## Run

```bash
python run.py
```

## HRR Assets

Place HRR plate images and icon files in:

```text
color_vision_tests/assets/hrr/
```

Example files:

- `Test1.png` to `Test16.png`
- `圆.png`
- `叉.png`
- `三角.png`
- `进.png`
- `准备.png`

The answer key file should be placed at:

```text
color_vision_tests/data/hrr_keys.json
```

Example format:

```json
[
  {
    "plate_id": "Test1",
    "positions": ["circle", "blank", "blank", "cross"]
  },
  {
    "plate_id": "Test2",
    "positions": ["cross", "triangle", "blank", "blank"]
  }
]
```

Position order is:

```text
0 1
2 3
```

That is:

- `positions[0]` = top-left
- `positions[1]` = top-right
- `positions[2]` = bottom-left
- `positions[3]` = bottom-right

## Output

Test results are exported as CSV files to:

```text
outputs/
```

## Notes

This repository is intended for research, teaching, and software demonstration purposes.

## License

This project is intended for academic and research use. Please add an appropriate license before public release.
