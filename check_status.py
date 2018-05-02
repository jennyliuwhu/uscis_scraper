import re
import cStringIO
import argparse
from bs4 import BeautifulSoup
import pycurl
import time

__author__ = 'jialingliu'

url = 'https://egov.uscis.gov/casestatus/mycasestatus.do'
results = []


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
        last_updated_date = get_case_last_updated_date(details)
        case_type = get_case_type(result[2])
        reason = details[3]
        info = {'CaseNum': case_num, 'Type': case_type, 'Status': result[1], 'LastUpdatedAt': last_updated_date,
                'Reason': reason}

        if verbose:
            print info

    except Exception:
        print 'USCIS format is incorrect'

    results.append(info)
    return info


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


def get_case_last_updated_date(details):
    year = str(details[1][1:])

    if year.isdigit():
        last_updated_date = details[0][3:] + ' ' + details[1][1:]
    else:
        last_updated_date = None

    return last_updated_date


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

    get_range(case_number, range, args.verbose)

    results = filter(lambda i: len(i.keys()) != 0, results)
    print results


def cmd_argument_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--range', required=False, type=int, help='Range Number')
    parser.add_argument('-c', '--case_num', required=True, type=str, help='Case Number, prefix needed')
    parser.add_argument('-v', '--verbose', action="store_true", help='Verbose mode will print out more information')
    return parser.parse_args()


if __name__ == '__main__':
    main()
