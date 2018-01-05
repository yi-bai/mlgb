from apiclient import discovery

def make_matrix(twod):
	max_size = max([len(row) for row in twod])
	for row in twod:
		row += ['' for i in range(max_size - len(row))]
	return twod

class GoogleSheet:
	def __init__(self, developerKey):
		self.service = discovery.build('sheets', 'v4', developerKey=developerKey)
		self.spreadsheetRangeCache = {}

	# return first sheet
	def getSpreadsheet(self, spreadsheetId):
		# get spread sheet
		spreadsheet = self.service.spreadsheets().get(spreadsheetId=spreadsheetId).execute()
		firstSheetRange = spreadsheet["sheets"][0]["properties"]["title"]+'!A1:ZZ'
		result = make_matrix(self.service.spreadsheets().values().get(spreadsheetId=spreadsheetId, range=firstSheetRange).execute()
			.get("values", []))
		self.spreadsheetRangeCache[firstSheetRange] = result
		self.spreadsheetId = spreadsheetId
		return result

	def getRange(self, range):
		try: range.index("!")
		except ValueError: range+="!A1:ZZ"
		if range in self.spreadsheetRangeCache:
			return self.spreadsheetRangeCache[range]
		result = make_matrix(self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId, range=range).execute()
			.get("values", []))
		self.spreadsheetRangeCache[range] = result
		return result