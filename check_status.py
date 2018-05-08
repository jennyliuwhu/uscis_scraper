import re
import cStringIO
import argparse
from bs4 import BeautifulSoup
import pycurl
import time
import MySQLdb
from datetime import datetime
from pytz import timezone
import pytz

__author__ = 'jialingliu'

url = 'https://egov.uscis.gov/casestatus/mycasestatus.do'
results = []
date_format = '%m/%d/%Y %H:%M:%S %Z'

db = MySQLdb.connect("localhost", "root", "12345678", "uscis")
cursor = db.cursor()
select_query_format = 'SELECT * FROM uscis.case_status WHERE center="{}" AND case_num={}'
insert_query_format = 'INSERT INTO uscis.case_status (case_num, case_year, case_type, case_reason, case_status, ' \
                      'center, receive_date, case_updated_date, last_updated_at) ' \
                      'VALUES ({}, {}, "{}", "{}", "{}", "{}", "{}", "{}", "{}")'
update_query_format = 'UPDATE uscis.case_status SET case_num={}, case_year={}, case_type="{}", case_reason="{}", ' \
                      'case_status="{}", center="{}", receive_date="{}", case_updated_date="{}", last_updated_at="{}" ' \
                      'WHERE center="{}" AND case_num={}'


def query(case_num, verbose):
    info = {}
    result = ''
    buf = cStringIO.StringIO()
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.POSTFIELDS, 'appReceiptNum=%s' % case_num)
    c.setopt(c.WRITEFUNCTION, buf.write)
    c.perform()

    soup = BeautifulSoup(buf.getvalue(), "html.parser")
    case_txt = soup.findAll("div", {"class": "rows text-center"})

    for i in case_txt:
        result = result + i.text

    result = result.split('\n')
    buf.close()
    try:
        details = result[2].split(',')
        case_updated_date = get_case_case_updated_date(details)
        case_type = get_case_type(result[2])
        reason = details[3]
        info = {'CaseNum': case_num, 'Type': case_type.strip(), 'Status': result[1].strip(),
                'LastUpdatedAt': case_updated_date.strip(),
                'Reason': reason.strip()}

        if verbose:
            print info

    except Exception:
        print 'USCIS format is incorrect'
    insert_into_db(info)
    results.append(info)
    return info


def insert_into_db(info):
    global cursor
    global date_format
    if len(info.keys()) != 0:
        center = info['CaseNum'][:3]
        case_num = info['CaseNum'][3:]
        case_year = case_num[:2]
        receive_date = None if (info['Status'].find("Received") == -1) else info['LastUpdatedAt']
        select_query = select_query_format.format(center, case_num)
        print select_query
        cursor.execute(select_query)
        count = cursor.rowcount
        date_format = '%m/%d/%Y %H:%M:%S %Z'
        date = datetime.now(tz=pytz.utc)
        print 'Current date & time is:', date.strftime(date_format)
        now = date.astimezone(timezone('US/Pacific'))
        if count == 0:
            insert_query = insert_query_format.format(case_num, case_year, info['Type'], info['Reason'], info['Status'],
                                                      center, receive_date, info['LastUpdatedAt'], now)
            print insert_query
            cursor.execute(insert_query)
        else:
            row = cursor.fetchall()
            for data in row:
                receive_date = data[-2]
            update_query = update_query_format.format(case_num, case_year, info['Type'], info['Reason'], info['Status'],
                                                      center, receive_date, info['LastUpdatedAt'], now,
                                                      center, case_num)
            print update_query
            cursor.execute(update_query)
        db.commit()


def get_range(case_num, range, verbose):
    if not range:
        return query(case_num, verbose)
    case_int = int(case_num[3:])
    prefix = case_num[:3]
    query(case_num, verbose)
    while range > 0:
        greater = prefix + str(case_int + range)
        less = prefix + str(case_int - range)
        range -= 1
        query(greater, verbose)
        query(less, verbose)
        time.sleep(1)


def get_case_case_updated_date(details):
    year = str(details[1][1:])

    if year.isdigit():
        case_updated_date = details[0][3:] + ' ' + details[1][1:]
    else:
        case_updated_date = None

    return case_updated_date


def get_case_type(line):
    i_case = re.search("\w*I-\w*", line)

    if i_case:
        return i_case.group(0)
    else:
        return 'Unsupported Case Type'


def main():
    global results
    args = cmd_argument_parser()
    case_number = args.case_num
    range = args.range

    create_table()

    get_range(case_number, range, args.verbose)

    results = filter(lambda i: len(i.keys()) != 0, results)
    print results

    cursor.close()
    db.close()


def create_table():
    global cursor
    query = 'create table IF not EXISTS uscis.case_status (' \
            'id INT NOT NULL AUTO_INCREMENT, ' \
            'case_num INT NOT NULL, ' \
            'case_year INT NOT NULL, ' \
            'case_type VARCHAR(25) NOT NULL, ' \
            'case_reason VARCHAR(100) NOT NULL, ' \
            'case_status VARCHAR(1000) NOT NULL, ' \
            'center VARCHAR(10) NOT NULL, ' \
            'receive_date VARCHAR(45) DEFAULT NULL, ' \
            'case_updated_date VARCHAR(45) DEFAULT NULL, ' \
            'last_updated_at VARCHAR(45) NOT NULL, ' \
            'PRIMARY KEY (id))ENGINE=InnoDB;'
    cursor.execute(query)


def cmd_argument_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--range', required=False, type=int, help='Range Number')
    parser.add_argument('-c', '--case_num', required=True, type=str, help='Case Number, prefix needed')
    parser.add_argument('-v', '--verbose', action="store_true", help='Verbose mode will print out more information')
    return parser.parse_args()


if __name__ == '__main__':
    main()
