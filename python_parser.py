from apiclient import discovery
import json, time

discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?version=v4')
service = discovery.build('sheets', 'v4', developerKey='AIzaSyDk90mbxnE2U3nl0xf00djXH0LfmGYQfZ4')

def get_file(spreadsheetId):
	result = service.spreadsheets().values().get(spreadsheetId=spreadsheetId, range='sheet2!A1:ZZ').execute()
	return result.get('values', [])

def make_matrix(twod):
	max_size = max([len(row) for row in twod])
	for row in twod:
		row += ['' for i in range(max_size - len(row))]
	return twod

class MatrixAccessor:
	matrix = [[]]
	(start_row, start_col, len_row, len_col) = (0, 0, 0, 0)

	def __init__(self, matrixOrAccessor, start_row, start_col, len_row = None, len_col = None):
		if not isinstance(matrixOrAccessor, MatrixAccessor):
			self.matrix = matrixOrAccessor
			(self.start_row, self.start_col, self.len_row, self.len_col) = (start_row, start_col, len_row, len_col)
		else:
			self.matrix = matrixOrAccessor.matrix
			self.start_row += matrixOrAccessor.start_row + start_row
			self.start_col += matrixOrAccessor.start_col + start_col
			(self.len_row, self.len_col) = (len_row, len_col)

	def getRow(self, row):
		if self.len_col:
			return self.matrix[row + self.start_row][self.start_col:self.start_col + self.len_col]
		else:
			return self.matrix[row + self.start_row][self.start_col:]

	def getCell(self, row, col):
		return self.matrix[row + self.start_row][col + self.start_col]

	def setCell(self, row, col, value):
		self.matrix[row + self.start_row][col + self.start_col] = value

	def getWidth(self):
		return self.len_col if self.len_col else len(self.matrix[0]) - self.start_col

	def getHeight(self):
		return self.len_row if self.len_row else len(self.matrix) - self.start_row

class MlgbNoContent:
	def __init__(self):
		return

def mlgb(accessor):
	if not isinstance(accessor.getCell(0,0), basestring):
		return accessor.getCell(0,0)

	(height, width) = (accessor.getHeight(), accessor.getWidth())
	if height == 0 or width == 0:
		return MlgbNoContent()
	elif (height == 1 or not accessor.getCell(1,0)) and (width == 1 or not accessor.getCell(0,1)):
		return parseJsonString(accessor.getCell(0,0)) if accessor.getCell(0,0) != "" else MlgbNoContent()
	elif accessor.getCell(0,0) == "-":
		return mlgbList(accessor)
	elif accessor.getCell(0,0) == "#":
		return mlgbSharp(accessor)
	else:
		return mlgbObject(accessor)

def parseJsonString(string):
	if string == "TRUE": return True
	if string == "FALSE": return False
	try: return json.loads(string)
	except ValueError: return string

def mlgbList(accessor):
	indexRowsNumbers = []
	for i in range(accessor.getHeight()):
		cell = accessor.getCell(i,0)
		if cell == '-':
			indexRowsNumbers.append(i)
		elif cell:
			return []
	elems = []
	lenIndexRowNumbers = len(indexRowsNumbers)
	for i, indexRowsNumber in enumerate(indexRowsNumbers):
		accessorHeight = indexRowsNumbers[i+1] - indexRowsNumber if i != lenIndexRowNumbers - 1 else accessor.getHeight() - indexRowsNumber
		elems.append(mlgb(MatrixAccessor(accessor, indexRowsNumber, 1, accessorHeight, accessor.getWidth() - 1)))
	return filter(lambda x: not isinstance(x, MlgbNoContent), elems)

def mlgbObject(accessor):
	if accessor.getWidth() == 1:
		return None
	rowKeyList = []
	for i in range(accessor.getHeight()):
		cell = accessor.getCell(i,0)
		if cell: rowKeyList.append({"row": i, "key": cell})
	elems = []
	lenRowKeyList = len(rowKeyList)
	for i, rowKey in enumerate(rowKeyList):
		accessorHeight = rowKeyList[i+1]["row"] - rowKey["row"] if i != lenRowKeyList - 1 else accessor.getHeight() - rowKey["row"]
		elems.append({
			"keys": rowKey["key"] if rowKey["key"]=="..." else rowKey["key"].split("."),
			"value": mlgb(MatrixAccessor(accessor, rowKey["row"], 1, accessorHeight, accessor.getWidth() - 1))
		})
	# Expand ...
	if len(elems) == 1 and elems[0]["keys"]=="...":
		return elems[0]["value"]

	# Concat result
	result = {}
	for elem in elems:
		if elem["keys"] == "..." and isinstance(elem["value"], dict):
			result.update(elem["value"])
		else:
			curObject = result
			# set keys en route
			for key in elem["keys"][0:-1]:
				if key not in curObject:
					curObject[key] = {}
				curObject = curObject[key]
			if not isinstance(elem["value"], MlgbNoContent):
				curObject[elem["keys"][-1]] = elem["value"]
	return result if len(result.keys()) else None

def mlgbSharp(accessor):
	def findSquareSharps(accessor):
		sharpRows = 0
		for i in range(accessor.getHeight()):
			if accessor.getCell(i,0) == "#": sharpRows = i + 1
			else: break
		sharpCols = 0
		for j in range(accessor.getWidth()):
			if accessor.getCell(0,j) == "#": sharpCols = j + 1
			else: break
		for i in range(sharpRows):
			if i == 0: continue
			for j in range(sharpCols):
				if j == 0: continue
				if accessor.getCell(i, j) != "#": return (0,0)
		return (sharpRows,sharpCols)

	def findRowsWithKeys(accessor):
		ret = []
		for i in range(accessor.getHeight()):
			for j in range(accessor.getWidth()):
				if accessor.getCell(i, j) != "":
					ret.append(i)
					break
		return ret

	def findColsWithKeys(accessor):
		ret = []
		for j in range(accessor.getWidth()):
			for i in range(accessor.getHeight()):
				if accessor.getCell(i, j) != "":
					ret.append(j)
					break
		return ret

	def diffLens(lenList, allLen):
		list1 = [0] + lenList
		list2 = lenList + [allLen]
		return [list2_i - list1_i for list1_i, list2_i in zip(list1, list2)][1:]

	def transposeMatrixAccessor(accessor):
		matrix = []
		for j in range(accessor.getWidth()):
			row = []
			for i in range(accessor.getHeight()):
				row.append(accessor.getCell(i,j))
			matrix.append(row)
		return MatrixAccessor(matrix, 0, 0)

	def insertContentWithRowAxis(contents, accessor, isAxisEmpty):
		if isAxisEmpty: return contents[0]
		contentIndex = 0
		matrix = []
		for i in range(accessor.getHeight()):
			row = accessor.getRow(i) + [""]
			for j in reversed(range(-len(row), 0)):
				if(row[j] != ""):
					row[j+1] = contents[contentIndex]
					contentIndex += 1
					break
			matrix.append(row)
		return mlgb(MatrixAccessor(matrix, 0, 0))

	# find square sharps in left-top corner
	(sharpRows, sharpCols) = findSquareSharps(accessor)
	if not sharpRows or not sharpCols: return MlgbNoContent()

	rowAxisMatrixAccessor = MatrixAccessor(accessor, sharpRows, 0, accessor.getHeight() - sharpRows, sharpCols)
	colAxisMatrixAccessor = MatrixAccessor(accessor, 0, sharpCols, sharpRows, accessor.getWidth() - sharpCols)
	colAxisTransposeMatrixAccessor = transposeMatrixAccessor(colAxisMatrixAccessor)

	rowsWithKeys = [sharpRows + e for e in findRowsWithKeys(rowAxisMatrixAccessor)]
	colsWithKeys = [sharpCols + e for e in findColsWithKeys(colAxisMatrixAccessor)]

	# empty row keys or col keys
	(isRowWithKeysEmpty, isColWithKeysEmpty) = (not len(rowsWithKeys), not len(colsWithKeys))
	if isRowWithKeysEmpty: rowsWithKeys = [sharpRows]
	if isColWithKeysEmpty: colsWithKeys = [sharpCols]

	rowsLens = diffLens(rowsWithKeys, accessor.getHeight())
	colsLens = diffLens(colsWithKeys, accessor.getWidth())

	contentsMatrix = []
	# get contents of cells
	for i in range(len(rowsWithKeys)):
		contentsRow = []
		for j in range(len(colsWithKeys)):
			contentsRow.append(mlgb(MatrixAccessor(accessor, rowsWithKeys[i], colsWithKeys[j], rowsLens[i], colsLens[j])))
		contentsMatrix.append(contentsRow)

	contentsRow = [insertContentWithRowAxis(row, colAxisTransposeMatrixAccessor, isColWithKeysEmpty) for row in contentsMatrix]
	return insertContentWithRowAxis(contentsRow, rowAxisMatrixAccessor, isRowWithKeysEmpty)

ctx_matrix = make_matrix(get_file('1yX-Ixjc0a8DGSvWys13rYqASR9DffnBeQXWJIyAgVVk'))
start_time = time.time()
print 'start parsing'
res = mlgb(MatrixAccessor(ctx_matrix, 0, 0))
print 'end parsing', time.time() - start_time
print json.dumps(res)