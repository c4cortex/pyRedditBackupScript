# pyRedditBackupScript
Python script to backup saved reddit images and videos

It can be used to create as a basis of a local backup of the images and videos saved on the user's reddit account.

Besides standard packages, it nees praw and requests to be installed, and the praw credentials (see https://praw.readthedocs.io/en/latest/getting_started/authentication.html#oauth ).

Using it should in the best case be straightforward: execute the script, select a folder to store the backup in and wait for it to finish. So far it is only adapted for the cases I needed and thus might need some changes for other users.
