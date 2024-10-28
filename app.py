from utils import *

if __name__ == '__main__':
    db_connection = SQLConnection()
    inserter = PayrollDataInserter(db_connection)

    for xml_file in glob.glob('files/*.xml'):
        processor = PayrollProcessor(xml_file)
        processor.extract_data()
        inserter.insert_data(processor.data)

    db_connection.close()