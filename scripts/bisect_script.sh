#!/bin/bash
COMMIT=${1:-$(git rev-parse BISECT_HEAD)}

echo "Bisecting at commit $COMMIT"

# Make the right version of dafny
if [[ $(pwd) != */dafny ]]; then
  cd dafny
fi
git checkout $COMMIT
echo "Building Dafny"
# Check if the make command failed
if ! make exe > /dev/null 2>&1; then
  make clean > /dev/null 2>&1
  if ! make exe > /dev/null 2>&1; then
    echo "Dafny failed to build"
  fi
else
  echo "Dafny built successfully"
fi

echo $(dafny /version)

echo "Building Z3"
yes All | make z3-ubuntu > /dev/null 2>&1
cd ..

mkdir tmp
cp main.dfy tmp/main.dfy
cp interestingness_test.sh tmp/interestingness_test.sh
echo "Running interestingness test"
cd tmp
timeout 600 ./interestingness_test.sh 2>&1
exit_status=$?
cd ..
rm -rf tmp

# If the timeout is reached, exit with status 125 to indicate the commit should be skipped
if [ $exit_status -eq 1 ]; then
  echo "Result of commit $COMMIT is good."
  exit 0
elif [ $exit_status -eq 0 ]; then
  echo "Result of commit $COMMIT is bad."
  exit 1
else
  echo "Result of commit $COMMIT is $exit_status."
  exit 125
fi


