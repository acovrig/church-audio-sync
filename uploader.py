import paramiko
from os import path

class Uploader():

  def __init__(self, config, src, dst):
    self.src = src
    self.dst = dst
    self.fn = path.basename(src)
    self.config = config

  def upload(self):
    key = paramiko.RSAKey.from_private_key_file(self.config['key'])
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=self.config['host'], port=self.config['port'], username=self.config['user'], pkey=key)
    sftp = ssh.open_sftp()
    dirs = f"{self.config['dir']}/{self.dst}".split('/')
    dirs.pop(0)
    if self.config['dir'][0] == '/':
      sftp.chdir('/')
    for d in dirs:
      if d != '':
        if d not in sftp.listdir():
          sftp.mkdir(d)
        sftp.chdir(d)

    if self.fn in sftp.listdir():
      print(f'Skipping {self.fn}')
      return

    sftp.put(self.src, self.fn, self.upload_prog)
  
    print('Done')

  def upload_prog(self, i, t):
    if t > 0:
      per = round((i*100)/t)
      print(f'Upoaded {per}% ({i} of {t})')
