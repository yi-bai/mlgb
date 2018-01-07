import json, time, sys
from google_sheet import GoogleSheet

def get_file(spreadsheetId):
	result = service.spreadsheets().values().get(spreadsheetId=spreadsheetId, range='sheet2!A1:ZZ').execute()
	return result.get('values', [])

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

	def getMatrix(self):
		return self.getMatrixWithBound(0, self.getHeight(), 0, self.getWidth())

	def getMatrixWithBound(self, up, down, left, right):
		ret = []
		for i in range(up, down):
			row = []
			for j in range(left, right):
				row.append(self.getCell(i, j))
			ret.append(row)
		return ret

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

def mlgb(accessor, rangeGetter):
	if not isinstance(accessor.getCell(0,0), basestring):
		return accessor.getCell(0,0)

	(height, width) = (accessor.getHeight(), accessor.getWidth())
	#print height,width
	if height == 0 or width == 0:
		return MlgbNoContent()
	elif (height == 1 or not accessor.getCell(1,0)) and (width == 1 or not accessor.getCell(0,1)):
		return parseJsonString(accessor.getCell(0,0), rangeGetter) if accessor.getCell(0,0) != "" else MlgbNoContent()
	elif accessor.getCell(0,0) == "-":
		return mlgbList(accessor, rangeGetter)
	elif accessor.getCell(0,0) == "#":
		return mlgbSharp(accessor, rangeGetter)
	elif accessor.getCell(0,0) == '...':
		# has ..., - -> List
		allKeys = set([accessor.getCell(i,0) for i in range(height) if len(accessor.getCell(i,0))])
		if allKeys == set(['-', '...']):
			return mlgbList(accessor, rangeGetter)
		else:
			return mlgbObject(accessor, rangeGetter)
	else:
		return mlgbObject(accessor, rangeGetter)

def parseJsonString(string, rangeGetter):
	if string == "TRUE": return True
	if string == "FALSE": return False
	try: return json.loads(string)
	except ValueError:
		if string.startswith("mlgb://"): return mlgb(MatrixAccessor(rangeGetter(string[7:]), 0, 0), rangeGetter)
		return string

def mlgbList(accessor, rangeGetter):
	indexRowsNumbers = []
	for i in range(accessor.getHeight()):
		cell = accessor.getCell(i,0)
		if cell == '-' or cell == '...':
			indexRowsNumbers.append(i)
		elif cell:
			return []
	elems = []
	lenIndexRowNumbers = len(indexRowsNumbers)
	for i, indexRowsNumber in enumerate(indexRowsNumbers):
		accessorHeight = indexRowsNumbers[i+1] - indexRowsNumber if i != lenIndexRowNumbers - 1 else accessor.getHeight() - indexRowsNumber
		mlgbResult = mlgb(MatrixAccessor(accessor, indexRowsNumber, 1, accessorHeight, accessor.getWidth() - 1), rangeGetter)
		if accessor.getCell(indexRowsNumber, 0) == '...':
			if isinstance(mlgbResult, list):
				elems += mlgbResult
		else:
			elems.append(mlgbResult)
	return filter(lambda x: not isinstance(x, MlgbNoContent), elems)

def mlgbObject(accessor, rangeGetter):
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
			"value": mlgb(MatrixAccessor(accessor, rowKey["row"], 1, accessorHeight, accessor.getWidth() - 1), rangeGetter)
		})

	# Expand ...
	if len(elems) == 1 and elems[0]["keys"]=="...":
		return elems[0]["value"]

	# if all keys are ... and values are all list then return list
	if set([elem['keys'] for elem in elems if not isinstance(elem['keys'], list)]) == set(['...']) and set([isinstance(elem['value'], list) for elem in elems]) == set([True]):
		ret = []
		for sublist in [elem['value'] for elem in elems]:
			for item in sublist:
				ret.append(item)
		return ret

	# Concat result
	result = {}
	for elem in elems:
		if elem["keys"] == "...":
			if isinstance(elem["value"], dict):
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

def mlgbSharp(accessor, rangeGetter):
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
		#find folded edge
		cellWithSharp = []
		# when multiple sharps appear, only the highest one will be used
		colsWithSharp = []
		cellFoldedEdgeMapping = {}

		for i in range(accessor.getHeight()):
			for j in range(accessor.getWidth()):
				#Folded edge (applying starts from second row)
				if accessor.getCell(i, j) == "#" and i > 0 and j not in colsWithSharp:
					cellWithSharp.append((i, j))
					colsWithSharp.append(j)

		#Folded edge
		for xy in cellWithSharp:
			#find next element of row above:
			up = xy[0]
			left = xy[1]
			down = accessor.getHeight()
			right = accessor.getWidth()
			for j in range(xy[1] + 1, accessor.getWidth()):
				if accessor.getCell(up - 1, j) != "":
					right = j
					break

			#copy this range to a new matrix
			cellFoldedEdgeMapping[xy] = accessor.getMatrixWithBound(up, down, left, right)

		#generate a new col
		cellToErase = []
		for cell, matrix in cellFoldedEdgeMapping.items():
			for i in range(len(matrix)):
				for j in range(len(matrix[0])):
					cellToErase.append((cell[0]+i, cell[1]+j))

		matrixWithoutFoldedEdge = []
		for i in range(accessor.getHeight()):
			row = []
			for j in range(accessor.getWidth()):
				row.append(accessor.getCell(i,j) if (i,j) not in cellToErase else "")
			matrixWithoutFoldedEdge.append(row)
		matrixWithoutFoldedEdge = MatrixAccessor(matrixWithoutFoldedEdge, 0, 0)

		colsWithKeys = []

		for i in range(matrixWithoutFoldedEdge.getHeight()):
			for j in range(matrixWithoutFoldedEdge.getWidth()):
				#columns with key
				if matrixWithoutFoldedEdge.getCell(i, j) != "" and j not in colsWithKeys:
					colsWithKeys.append(j)

		colsWithKeys.sort()
		return (colsWithKeys, cellFoldedEdgeMapping, matrixWithoutFoldedEdge)

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
		return mlgb(MatrixAccessor(matrix, 0, 0), rangeGetter)

	#delete empty last rows
	def clearLastEmptyRows(matrix):
		downRow = len(matrix)
		for i in range(len(matrix)):
			if matrix[i][0] == "":
				downRow = i
				break
		return matrix[0:downRow]

	# find square sharps in left-top corner
	(sharpRows, sharpCols) = findSquareSharps(accessor)
	if not sharpRows or not sharpCols: return MlgbNoContent()

	rowAxisMatrixAccessor = MatrixAccessor(accessor, sharpRows, 0, accessor.getHeight() - sharpRows, sharpCols)
	colAxisMatrixAccessor = MatrixAccessor(accessor, 0, sharpCols, sharpRows, accessor.getWidth() - sharpCols)

	rowsWithKeys = [sharpRows + e for e in findRowsWithKeys(rowAxisMatrixAccessor)]
	#columns with keys, and folded edge will be found
	(colsWithKeys, cellFoldedEdgeMapping, matrixWithoutFoldedEdge) = findColsWithKeys(colAxisMatrixAccessor)
	colsWithKeys = [sharpCols + e for e in colsWithKeys]

	#print matrixWithoutFoldedEdge.getMatrix()
	colAxisTransposeMatrixAccessor = transposeMatrixAccessor(matrixWithoutFoldedEdge)
	colFoldedEdgeMapping = {k[1]+sharpCols:clearLastEmptyRows(v) for (k,v) in cellFoldedEdgeMapping.items()}

	# empty row keys or col keys
	(isRowWithKeysEmpty, isColWithKeysEmpty) = (not len(rowsWithKeys), not len(colsWithKeys))
	if isRowWithKeysEmpty: rowsWithKeys = [sharpRows]
	if isColWithKeysEmpty: colsWithKeys = [sharpCols]

	rowsLens = diffLens(rowsWithKeys, accessor.getHeight())
	colsLens = diffLens(colsWithKeys, accessor.getWidth())

	#print colFoldedEdgeMapping, colsWithKeys

	contentsMatrix = []
	# get contents of cells
	for i in range(len(rowsWithKeys)):
		contentsRow = []
		for j in range(len(colsWithKeys)):
			if colsWithKeys[j] not in colFoldedEdgeMapping:
				matrixAccessor = MatrixAccessor(accessor, rowsWithKeys[i], colsWithKeys[j], rowsLens[i], colsLens[j])
			else:
				upper = colFoldedEdgeMapping[colsWithKeys[j]] #folded edge
				#print "hehe",rowsWithKeys[i], colsWithKeys[j], rowsLens[i], colsLens[j]
				lower = accessor.getMatrixWithBound(rowsWithKeys[i], rowsWithKeys[i]+rowsLens[i], colsWithKeys[j], colsWithKeys[j]+colsLens[j])
				#print upper+lower
				matrixAccessor = MatrixAccessor(upper+lower, 0, 0)
			#print matrixAccessor.getMatrix()
			contentsRow.append(mlgb(matrixAccessor, rangeGetter))
		contentsMatrix.append(contentsRow)

	contentsRow = [insertContentWithRowAxis(row, colAxisTransposeMatrixAccessor, isColWithKeysEmpty) for row in contentsMatrix]
	return insertContentWithRowAxis(contentsRow, rowAxisMatrixAccessor, isRowWithKeysEmpty)

def parse(spreadsheetId):

	googleSheet = GoogleSheet('AIzaSyDk90mbxnE2U3nl0xf00djXH0LfmGYQfZ4')
	contents = googleSheet.getSpreadsheet(spreadsheetId)

	res = mlgb(MatrixAccessor(contents, 0, 0), googleSheet.getRange)
	return json.dumps(res, ensure_ascii=False).encode("utf8")