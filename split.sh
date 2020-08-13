#!/usr/bin/env bash

# Take a word list file (one word per line) and partition
# it across a user defined number of bins (files). New
# files will be put in current directory

if [[ $# != 2 ]]
then
    echo "uasge: split.sh <# equal parts> <word_list>"
    exit 1
fi

num_of_files=$1
word_list=$2

if [[ "$num_of_files" -lt 1 ]]
then
    echo "<# equal parts> must be greater than 0."
    exit 1
fi

total_lines=$(wc -l <${word_list})
((lines_per_file = (total_lines + num_of_files - 1) / num_of_files))

split --lines=${lines_per_file} -a 3 ${word_list} $(basename $word_list.)
if [[ $? -ne 0 ]]
then
    echo "Error encountered. Exiting."
    exit 1
fi

wc -l $(basename $word_list).*
