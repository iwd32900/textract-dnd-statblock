#!/usr/bin/env python3
import json
import sys

import boto3

def main(infiles):
    txt = boto3.client('textract')
    for infile in infiles:
        print(infile)
        with open(infile, 'rb') as stream:
            contents = stream.read()
        output = txt.detect_document_text(Document=dict(Bytes=contents))
        with open(infile+'.textract.json', 'w') as outfile:
            json.dump(output, outfile, sort_keys=False, indent=2)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
