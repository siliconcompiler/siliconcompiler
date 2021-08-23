=========================
Client / Server Interface
=========================

The SiliconCompiler project is capable of deferring jobs to a remote server using the same general syntax as its local build system. The project ships with a minimal open-source development server, but the client / server API is designed to be simple and robust enough to support other server implementations, including proprietary ones such as the `server.siliconcompiler.com` backend.

This page will introduce the development server, the data encryption model, and the process of running a design on a remote cluster. It also includes auto-generated descriptions of each API endpoint, and the JSON parameters that they expect.

Basic Usage: Server
-------------------

When you install the siliconcompiler Python package, the `sc-server` command is added to your system path along with the main `sc` application. This is a minimal development server which implements the core workflow for two scenarios: un-authenticated plaintext data, and authenticated encrypted data which requires a user account.

The `sc-server` script is only intended for testing and development purposes. We do not recommend using it in situations where data privacy is critical, and we recommend against exposing it to the wider internet. If you do choose to use this server for non-trivial applications, we recommend only exposing the port that it runs on to a small private network.

SYNOPSIS
========

`sc-server [-nfs_mount [/path/to/working/dir]] [-cluster [slurm|local]] [-port [number]] [-auth]`

OPTIONS
=======

-nfs_mount
++++++++++

The `-nfs_mount` option specifies a working directory for the development server. In a computing cluster, this will typically be an NFS or other networked storage drive. But you can specify any directory on your system, and you will probably want to use a local file path with the `-cluster local` option.

-cluster
++++++++

The `-cluster` option specifies whether the server is also a 'control node' in an HPC cluster. Currently, only Slurm clusters are supported for un-authenticated jobs (`-cluster slurm`).

You can also run the compute workloads on the server host with `-cluster local`. You should use this option if you are running the server on a single machine, such as a laptop.

-port
+++++

The `-port` option specifies which port the server should accept connections on. It accepts a number, and defaults to port 8080.

-auth
+++++

The `-auth` option is a Boolean flag, and it determines whether authentication and encryption should be enabled on the server. If this flag is included, the server will look for a `users.json` file in the working directory specified with the `-nfs_mount` option.

The `users.json` file follows a simple JSON format to map usernames to a base64-encoded RSA public key::

    {
      "users": [
        {
          "username": "user1",
          "pub_key": "ssh-rsa [...]"
        },
        {
          "username": "user2",
          "pub_key": "ssh-rsa [...]"
        }
        [,...]
      ]
    }

Typically, the public key string will be the contents of your `[key_name].pub` file.

Please remember that this minimal test server is only intended to demonstrate how the core cryptographic scheme works. We do not recommend exposing it to the wider internet or using it to handle sensitive data.

EXAMPLES
========

Quickstart: start a server on its default port with no authentication support::

    mkdir -p server_work/
    sc-server -nfs_mount server_work/ -cluster local

Create a key pair for a test user, and start a server with asymmetric key authentication support::

    ssh-keygen -t rsa -b 4096 -C '' -N '' -f [/path/to/new/keys]
    echo "{\"users\":[{\
           \"username\":\"test_user\",\
           \"pub_key\":\"$(cat [/path/to/new/keys].pub)\"}]}" > server_work/users.json
    sc-server -nfs_mount server_work/ -cluster local -auth

Basic Usage: Client
-------------------

The remote client built into the `sc` app has two modes of operation: one which transmits data as plaintext, and one which encrypts data on the client-side using a pre-determined key pair. In both cases, the remote workflow can be run by adding a few `-remote_*` configuration flags to an ordinary `sc` command.

SYNOPSIS
========

`sc <source_files> [...design-specific configs...] [-remote_addr [hostname]] [-remote_port [number]] [-remote_user [username]] [-remote_key [/path/to/private/key]]`

OPTIONS
=======

-remote_addr
++++++++++++

The `-remote_addr` option specifies the hostname of the remote server. It could be an IP address if you are testing on a cloud host or subnet. It could also be a URL if you are connecting to a production server with valid DNS records.

Note that servers are not required to process un-authenticated job requests. If you attempt to run a job on a production backend such as `server.siliconcompiler.com` without authentication parameters, it may be rejected.

-remote_port
++++++++++++

The `-remote_port` option specifies the port which the remote server is running on. This may be an arbitrary port such as `8000` or `8080` on a development server, or it may be a more common port such as `443` on a production server with TLS-encrypted communications.

-remote_user
++++++++++++

The `-remote_user` option specifies a username for authenticating a job request. Each server is expected to maintain a one-to-one mapping of usernames to asymmetric public keys.

When a user needs to authenticate a request, they provide the username and the private half of the key pair. This both confirms their identity, and provides the server with the necessary information to decrypt the user's data for processing. In a production setting, the server must be trusted not to store or log that key, and client/server communications must be encrypted on the wire.

-remote_key
+++++++++++

The `-remote_key` option specifies a file path pointing to an SSH-encoded RSA private key, for authenticating a job request. SSH-encoded RSA keys typically do not have file extensions, and they are often stored in a user's `~/.ssh/` directory.

When a user needs to authenticate a request, they provide the username and the private half of the key pair. This both confirms their identity, and provides the server with the necessary information to decrypt the user's data for processing. In a production setting, the server must be trusted not to store or log that key, and client/server communications must be encrypted on the wire.

EXAMPLES
========

The following command can be used to build the trivial `gcd` example locally using the FreePDK45 PDK with a die size inferred from post-synthesis estimates::

    sc examples/gcd/gcd.v \
       -constraint examples/gcd/gcd.sdc \
       -design gcd \
       -target freepdk45_asicflow \
       -asic_density 10 \
       -asic_aspectratio 1 \
       -asic_coremargin 25

In order to run the same job on a remote server without authentication, you can start a local server::

    mkdir -p server_work
    sc-server -nfs_mount server_work -cluster local

And then add `-remote_addr [hostname] -remote_port [number]` to the local build command::

    sc examples/gcd/gcd.v \
       -constraint examples/gcd/gcd.sdc \
       -design gcd \
       -target freepdk45_asicflow \
       -asic_density 10 \
       -asic_aspectratio 1 \
       -asic_coremargin 25 \
       -remote_addr localhost \
       -remote_port 8080

If you followed the server examples to set up a test user account for authentication and started your server with the `-auth` option, you can run the remote job with at-rest data encryption by adding the `-remote_user [username] -remote_key [/path/to/private/key]` options::

    sc examples/gcd/gcd.v \
       -constraint examples/gcd/gcd.sdc \
       -design gcd \
       -target freepdk45_asicflow \
       -asic_density 10 \
       -asic_aspectratio 1 \
       -asic_coremargin 25 \
       -remote_addr localhost \
       -remote_port 8080 \
       -remote_user test_user \
       -remote_key [/path/to/private/key]

The key will be transmitted over the wire, so it is very important to use port 443 to enable TLS encryption when communicating with a server which is not on a local network. However, configuring a valid HTTPS certificate for a host is beyond the scope of these tutorials. Once again, this example development server is not intended for production use, and we cannot recommend using it to protect confidential designs or IP.

Production implementations of the server API, such as server.siliconcompiler.com, must be careful to avoid logging the private key or otherwise storing it on disk. They must also support HTTPS connections to ensure that the key can be encrypted in transit.

API Reference
-------------

.. clientservergen::
