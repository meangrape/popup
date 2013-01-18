import os


def set_env(hostname, configfile):
    os.environ['ANSIBLE_HOST'] = hostname
    os.environ['ANSIBLE_TRANSPORT'] = 'ssh'
    os.environ['ANSIBLE_SSH_ARGS'] = '-F %s' % configfile


def ssh_config(hostname, keyfile):
    configfile = './config/ssh_config/%s' % hostname
    with open(CFG, 'w') as f:
        f.write('SendEnv LANG LC_* GIT_*')
        f.write('HashKnownHosts yes')
        f.write('GSSAPIAuthentication yes')
        f.write('GSSAPIDelegateCredentials no')
        f.write('\n')
        f.write('Host ' % hostname)
        f.write('\tIdentityFile ' % keyfile)
        f.write('\tUser ubuntu')
        f.write('\tControlMaster auto')
        f.write('\tControlPath ssh_control/%r@h:@p')
        f.write('\tForwardAgent yes')
    set_env(hostname, configfile)
