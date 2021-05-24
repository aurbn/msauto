import os

RAW_ROOT = '/mnt/MSdata/'
DATA_ROOT = '/mnt/MSproc/'
DB_ROOT = '/home/msauto/db'
LOGNAME = 'msauto.log'
PROTOCOL_MAP = os.path.join(DB_ROOT, "protocol.map")
ORGANISM_MAP = os.path.join(DB_ROOT, "organism.map")
CONVERSION_CMD = '/home/msauto/msauto_venv/msauto/conv.sh {infile} {outdir}'
SCAFFOLD_CMD = '/home/msauto/Scaffold/ScaffoldBatch -f {infile}'
POSTPROC_CMD = 'Rscript --vanilla {script} {wd} {projname}'
CONF_DIR = '/mnt/MSproc/.conf'
TANDEM_TAXONOMY = os.path.join(CONF_DIR, 'taxonomy.xml')
TANDEM_DEFAULTS = '/home/msauto/msauto_venv/msauto/default_PROTEOME_MetOxilation_params.xml'
MASCOT_DEFAULTS = '/home/msauto/msauto_venv/msauto/UniProtKB-HS-20_Proteome_MetOxidation_TripleTOF.par'
TANDEM_CMD = '/home/msauto/bin/tandem-linux-17-02-01-4/bin/static_link_ubuntu/tandem.exe {infile}'
MASCOT_CGI = 'http://mascot.ripcm.com/mascot/cgi'
DB_CONV_FILE = os.path.join(DB_ROOT, "conversion.list")
DB_CONV_LOCK = 'DB_CONV_LOCK'
DB_IMPORTED_FILE = os.path.join(DB_ROOT, "imported.list")
DB_IMPORTED_LOCK = 'DB_IMPORTED_LOCK'
DB_TANDEM_FILE = os.path.join(DB_ROOT, "tandem.list")
DB_TANDEM_LOCK = 'DB_TANDEM_LOCK'
DB_MASCOT_FILE = os.path.join(DB_ROOT, "mascot.list")
DB_MASCOT_LOCK = 'DB_MASCOT_LOCK'
spreadsheetId = '1gayGq3w_eYMBCW6di5VX9FWVn7DBdJ8oafhm7QnvwK0'
CREDENTIALS_FILE = '/home/msauto/key.json'