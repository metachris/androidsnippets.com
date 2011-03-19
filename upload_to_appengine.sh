#!/bin/bash
set -e

function static_revert {
  # Set /static back to dev environment
  echo "Setting /static back to /html5-boilerplate"
  cd app
  rm static
  ln -s html5-boilerplate static
}

function static_toprod {
  echo "Setting /static to /html5-boilerplate/publish"
  # Set build script results as /static
  cd app
  rm static
  ln -s html5-boilerplate/publish static
  cd ..
}

function upload {
  # Upload to appengine
  set +e
  ~/Tools/google_appengine/appcfg.py update app
  set -e
}

function build {
  cd app/html5-boilerplate/build
  ant minify
}

read -p "Build the project with 'ant minify' now? [yN]" yn
  case $yn in
    [Yy]* ) build;;
    [Nn]* ) break;;
esac

static_toprod

read -p "You can test the final version now locally. Do you wish to upload this program? [yN]" yn
  case $yn in
    [Yy]* ) upload;;
    [Nn]* ) break;;
esac

static_revert


