import os

RAW_ROOT = '/home/urban/msauto_data/raws'
DATA_ROOT = '/home/urban/msauto_data/proc'
DB_ROOT = '/home/urban/msauto_data/db'
LOGNAME = 'msauto.log'
CONVERSION_CMD = '/home/urban/git/msauto/conv.sh {infile} {outdir}'
TANDEM_TAXONOMY = '/home/urban/git/msauto/taxonomy.xml'
TANDEM_DEFAULTS = '/home/urban/git/msauto/default_PROTEOME_MetOxilation_params.xml'
MASCOT_DEFAULTS = '/home/urban/git/msauto/UniProtKB-HS-20_Proteome_MetOxidation_TripleTOF.par'
TANDEM_CMD = '/home/urban/bin/tandem-linux-17-02-01-4/bin/static_link_ubuntu/tandem.exe {infile}'
MASCOT_CGI = 'http://194.85.9.127:180/mascot/cgi'
DB_CONV_FILE = os.path.join(DB_ROOT, "conversion.list")
DB_CONV_LOCK = 'DB_CONV_LOCK'
DB_IMPORTED_FILE = os.path.join(DB_ROOT, "imported.list")
DB_IMPORTED_LOCK = 'DB_IMPORTED_LOCK'
DB_TANDEM_FILE = os.path.join(DB_ROOT, "tandem.list")
DB_TANDEM_LOCK = 'DB_TANDEM_LOCK'
DB_MASCOT_FILE = os.path.join(DB_ROOT, "mascot.list")
DB_MASCOT_LOCK = 'DB_MASCOT_LOCK'
spreadsheetId = '1gayGq3w_eYMBCW6di5VX9FWVn7DBdJ8oafhm7QnvwK0'