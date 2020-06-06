# textract-dnd-statblock

This code uses AWS Textract to do Optical Character Recognition (OCR)
on Dungeons & Dragons (5e) monsters from the "Monster Manual" and "Volo's Guide to Monsters".
It then formats them in JSON compatible with [Improved Initiative](https://www.improved-initiative.com/),
a web-based combat tracker than makes the DM's life easier.

As inputs, it needs JPEG or PNG images, less than 5 MB, of *just* the monster's stat block.
It works well with iPhone images, for example, as long as you take a little care in lighting and cropping.
There are typically 1-2 mistakes per monster -- not perfect, but pretty impressive.
Most of that seems to be the choice of font -- Textract particularly dislikes the glyph for "1".

To start, you'll need:

- An AWS account
- AWS credentials configured (as for the AWS CLI)
- Python 3.6+ and the `boto3` library

The basic sequence of commands:
```
./image_to_textract.py *.jpg
./textract_to_monster.py *.textract.json
ls *.monster.json
```

## Algorithm

Textract gets us 80% of the way there;  the rest is my dumb heuristics.
The typography of D&D is highly consistent.
Mostly, we can rely on attributes appearing in a defined order,
and use simple string matching and regular expressions to get what we want.

Lines come out sorted top to bottom.
However, some stat blocks are two columns instead of one.
If a large enough fraction of text lines have their left edge past the image midline,
we declare a two-column stat block and sort those lines to the end.

The other trick is reliably detecting the vertical whitespace that separates paragraphs,
because the bounding box for any line of text can be a little wobbly.
I settled on measuring the distance between the middles of successive bounding boxes,
and comparing that to the median of such distances in the image.
This leads to pretty reliable detection of line breaks.

There are also a few cases where one wants to introduce hard line breaks,
such as lists of spells by level, and numbered lists of options within an Action.

There is one place where horizontal indentation replaces vertical whitespace
for separating actions, and that is the Legendary Actions block.