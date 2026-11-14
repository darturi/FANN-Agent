"""Private restore startup: inherited settings, max_connections32 for18 A/B readers."""
import hashlib,inspect,subprocess

def start(work):
 subprocess.run(['/opt/postgresql/bin/pg_ctl','-D',str(work/'pgdata'),'-l',str(work/'server.log'),'-w','-t','60','-o',
  "-c listen_addresses='' -c unix_socket_directories="+str(work/'socket')+
  ' -c unix_socket_permissions=0700 -c hba_file='+str(work/'pg_hba.conf')+
  ' -c shared_buffers=128MB -c max_connections=32 -c logging_collector=off -c log_statement=none -c log_min_error_statement=panic','start'],check=True)

def install(restore):
 previous=restore.__globals__['start'];source=inspect.getsource(previous)
 expected=" -c shared_buffers=128MB -c max_connections=16 -c logging_collector=off -c log_statement=none -c log_min_error_statement=panic"
 assert source.count(expected)==1 and previous.__module__=='database','inherited startup contract changed'
 restore.__globals__['start']=start
 return {'scope':'private copied restore only; inherited files unchanged','only_postgres_setting_change':'max_connections16->32','inherited_start_function_sha256':hashlib.sha256(source.encode()).hexdigest(),'max_connections':32}
