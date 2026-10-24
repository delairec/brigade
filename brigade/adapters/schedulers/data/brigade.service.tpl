[Unit]
Description=brigade tick

[Service]
Type=oneshot
KillMode=process
${environment}
ExecStart="${brigade}" tick --once
