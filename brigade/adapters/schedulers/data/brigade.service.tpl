[Unit]
Description=brigade tick

[Service]
Type=oneshot
${environment}
ExecStart="${brigade}" tick --once
