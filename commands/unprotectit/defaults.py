#!/usr/bin/env python3

BINDS = ['@upi', '@ttp']
CHANS = ['debug']
APIURL = {
    'unprotectit':   {'url': 'https://unprotect.it/api'},
    'attackmatrix':  {'url': 'http://149.210.137.179:8008/api/explore'},
}
CONTENTTYPE = 'application/json'
CACHE = 'commands/unprotectit/unprotectit.json'
LANGS = '''Actionscript, as, as3
AppleScript 	applescript
Bash 	bash, sh
Clojure 	clojure
CoffeeScript 	coffescript, coffee, coffee-script
C/C++ 	cpp, c++, c
C# 	cs, c#, csharp
CSS 	css
D 	d, dlang
Dart 	dart
Delphi 	delphi
Diff 	diff, patch, udiff
Django 	django
Dockerfile 	dockerfile, docker
Elixir 	elixir, ex, exs
Erlang 	erlang, erl
Fortran 	fortran
F# 	fsharp
G-Code 	gcode
Go 	go, golang
Groovy 	groovy
Handlebars 	handlebars, hbs, mustache
Haskell 	haskell, hs
Haxe 	haxe
Java 	java
JavaScript 	javascript, js
JSON 	json
Julia 	julia, jl
Kotlin 	kotlin
LaTeX 	latex, tex
Less 	less
Lisp 	lisp
Lua 	lua
Makefile 	makefile, make, mf, gnumake, bsdmake
Markdown 	markdown, md, mkd
Matlab 	matlab, m
Objective C 	objectivec, objective_c, objc
OCaml 	ocaml
Perl 	perl, pl
PostgreSQL 	pgsql, postgres, postgresql
PHP 	php, php3, php4, php5
PowerShell 	powershell, posh
Puppet 	puppet, pp
Python 	python, py
R 	r, s
Ruby 	ruby, rb
Rust 	rust, rs
Scala 	scala
Scheme 	scheme
SCSS 	scss
Smalltalk 	smalltalk, st, squeak
SQL 	sql
Stylus 	stylus, styl
Swift 	swift
Text 	text
TypeScript 	typescript, ts, tsx
VB.Net 	vbnet, vb, visualbasic
VBScript 	vbscript
Verilog 	verilog
VHDL 	vhdl
HTML, XML 	html, xml
YAML 	yaml, yml
'''
HELP = {
    'DEFAULT': {
        'args': None,
        'desc': 'Search unprotect.it for information and return any matching techniques, code snippets and YARA rules available. '
                'On its first run, the module will build a cache of the unprotect.it website, so the very first query will be '
                'slow.',
    },
    'rebuildcache': {
        'args': None,
        'desc': 'Force a rebuild of the cache. Please use this sparingly and do not overload the Unprotect.it website.',
    },
}
