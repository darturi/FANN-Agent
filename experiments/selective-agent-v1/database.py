"""A fresh private copy; SCRAM, Unix socket only, index verified before/after."""
import shutil
import subprocess
from design import read,save
from runtime_base import verify_index,verify_import


def start(work):
    subprocess.run(['pg_ctl','-D',str(work/'pgdata'),'-l',str(work/'server.log'),'-w','-t','60','-o',
        "-c listen_addresses='' -c unix_socket_directories="+str(work/'socket')+
        ' -c unix_socket_permissions=0700 -c hba_file='+str(work/'pg_hba.conf')+
        ' -c shared_buffers=128MB -c max_connections=16 -c logging_collector=off -c log_statement=none -c log_min_error_statement=panic','start'],check=True)


def stop(work):
    if (work/'pgdata/postmaster.pid').exists():
        subprocess.run(['pg_ctl','-D',str(work/'pgdata'),'-m','fast','-w','-t','60','stop'],check=True)


def prepare(package,bundle,prepared,work,frozen,extra_sql=''):
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo
    expected=read(package/'source-index.json')
    subprocess.run(['pg_verifybackup',str(prepared/'base')],check=True)
    frozen.initialize_auth(work)
    shutil.copytree(prepared/'base',work/'pgdata')
    shutil.copyfile(prepared/'admin.pgpass',work/'admin.pgpass')
    verify_index(work,expected);start(work)
    try:
        with psycopg.connect(make_conninfo(frozen.job_connection(work,admin=True),dbname='torch_reviews'),autocommit=True) as conn:
            password=(work/'reader.pgpass').read_text().strip().rsplit(':',1)[1]
            conn.execute(sql.SQL('ALTER ROLE torch_reader PASSWORD {}').format(sql.Literal(password)))
            conn.execute(frozen.FUNCTIONS+extra_sql)
            conn.execute('REVOKE ALL ON ALL FUNCTIONS IN SCHEMA fannagent FROM PUBLIC')
            conn.execute('GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA fannagent TO torch_reader')
        verify_import(frozen,bundle,work)
        save(work/'database-identity.json',expected)
        return expected
    except BaseException:
        stop(work);raise
