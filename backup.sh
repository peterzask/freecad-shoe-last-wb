#!/bin/bash
# Create directory if it doesn't exist
mkdir -p zBack
# Copy files with numbered backups, checking if files exist
if ls *.cfg 1> /dev/null 2>&1; then
    cp --backup=t *.{cfg,h,py,txt} zBack/
    echo "Backup completed."
else
    echo "No .cfg,h,py files found."
fi

