# uscis_scraper

### Usage:
* `python check_status.py -c CASE_NUM` gives you the status of the case. Besides, insert case status into mysql table `uscis.case_status`. 
* Run `python check_status.py --help` for more options. 
### Prerequisite
* Mysql installed
* Mysql database `uscis` pre-created

### Todos:
* Case status based on ranges
* Plot graphs
* ...