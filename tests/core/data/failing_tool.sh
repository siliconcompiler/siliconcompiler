#!/usr/bin/env bash

# This is a tool which outputs invalid UTF-8 chars and then errors out

echo test

echo -n -e '\xf5'

echo test

exit -1
