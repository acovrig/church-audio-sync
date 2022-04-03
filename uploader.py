import paramiko

class Uploader():

  def __init__(self, fn, config, sub, prog, cb):
    self.fn = fn
    self.sub = sub
    self.prog = prog
    self.cb = cb
    self.config = config

  def upload(self):
    key = paramiko.RSAKey.from_private_key_file(self.config['sftp_key'])
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=self.config['sftp_host'], port=self.config['sftp_port'], username=self.config['sftp_user'], pkey=key)
    sftp = ssh.open_sftp()
    sftp.chdir(self.config['upload_dir'])

    if self.fn in sftp.listdir():
      print(f'Deleting {self.fn}')
      sftp.remove(self.fn)
    self.sub.config(text=f'Uploading {self.fn}')
    sftp.put(f'{self.config["archive_base"]}\\{self.fn}', self.fn, self.upload_prog)
  
    print('Done')
    self.sub.pack_forget()
    self.prog.pack_forget()
    self.cb()

  def upload_prog(self, i, t):
    if t > 0:
      per = round((i*100)/t)
      if self.prog['value'] != per:
        print(f'Upoaded {per}% ({i} of {t})')
        self.prog.config(value=per)
