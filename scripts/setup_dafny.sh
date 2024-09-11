author=$1
branch=$2

git clone https://github.com/dafny-lang/dafny.git
cd dafny
git remote add merge-head https://github.com/$author/dafny.git
git fetch merge-head
git checkout -b $branch merge-head/$branch
make exe
make z3-ubuntu