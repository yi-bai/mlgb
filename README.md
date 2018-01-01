# mlgb
Markup Language, Grid-Based (MLGB)

parses sheets into a JSON.

MLGB grammer is defined recursively.

input of MLGB is a list of list of string.

by parsing top-left corner of input, the MLGB type is determined.

### No value
if first grid of first row is empty string, a special MLGB vlaue, `No value` is returned.

### Literal JSON value
if first row of input contains:
1) only one element;
2) first grid with non-empty string and second grid with empty string

the value is "Literal JSON value", which means:
if the string itself is a valid JSON, parser will return as its JSON value.
else, it would be the string as it is.

#### Special Literal JSON value
string `FALSE` will be parsed as JSON value `false`.
string `TRUE` will be parsed as JSON value `true`.
`"1"` will be parsed as string 1 instead of number 1, using similar value to represent number string.
`""` will be parsed as empty string, instead of `No value`.

### JSON-Object
if first grid of first row is not `-` or `#`, it will be parsed as a JSON object.
if first grid of first row is `-`, MLGB parser will scan through first column, if not all non-empty string are `-`, it will be parsed as a JSON object.
first, an empty result JSON object will be constructed.
then, scan through the first column of input. when a non-empty string is found, it is considered as a MLGB JSON-Object key.
let `i_this` and `i_next` be the index of row of this non-empty string and next non-empty string,
the MLGB value of (zero-index) range of row `[i_this, i_next)` and column of `[1, last_column]` will be the value of this key.

#### MLGB JSON-Object key
the key is a dot(`.`)-separated key representing the path of JSON object. as a special case, three dots (`...`) representing the root path.
value of three dots must be a valid JSON-Object value, and it would be merged with current return object. unless, the whole JSON-Object will be parsed as a `No value`.

if the JSON-Object value is `No value`, the key will not be added to the current result object.
if the key is already exists in result object, the value of this key will be overwritten.

### JSON-Array
if all non-empty values in first columns are `-`, it is parsed as a JSON array.
a JSON-Array is parsed similarly to JSON-Object. A `No value` element will not be appended to a JSON-array.

### MLGB-Sharp
if first grid of first row is `#`, it will be parsed as a "MLGB-Sharp".
...tbc
1. 找左上角的#块，将整个区域分割成四块
2. 找行的分块索引
3. 找列的分块索引，找的时候顺便找出折叠边，具体方法：按列-行的顺序找非空的单元格，当找到#时发现折叠边，折叠边1.不能是第一行，2.找#所在行的上一行，向右找第一个非空块，以#为左上边，第一个非空块为右边，整个列的底边为底边，将这一块放入折叠边块。与此同时，找列分块索引时跳过折叠边放入的所有列。
4. 按行列分块索引，将右下块分割，并将折叠边加入，求值
5. 将右下块插入到转置后的列块，将转置后的列块插入到行块，对行块求值，结束。
