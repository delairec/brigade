*/5 * * * * mkdir -p ${state_directory} && ${environment} ${brigade} tick --once >/dev/null 2>>${log_file} ${marker}
