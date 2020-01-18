export LC_ALL=en_GB.utf8

nodes=$(scontrol show hostnames $SLURM_JOB_NODELIST) # Getting the node names
nodes_array=( $nodes )
node1=${nodes_array[0]}
worker_num=${#nodes_array[@]}

echo "Starting ray cluster with, $worker_num, nodes"

ip_prefix=$(srun --nodes=1 --ntasks=1 -w $node1 hostname --ip-address) # Making address
echo $ip_prefix

suffix=':6379'
ip_head=$ip_prefix$suffix
export redis_password=$(uuidgen)
echo $redis_password

export ip_head # Exporting for latter access by trainer.py
echo "Starting head"
srun --nodes=1 --ntasks=1 -w $node1 ray start --block --head --redis-port=6379 --redis-password=$redis_password & # Starting the head
sleep 5

echo "Starting workers"
for ((  i=1; i<=$worker_num; i++ ))
do
  node2=${nodes_array[$i]}
  srun --nodes=1 --ntasks=1 -w $node2 ray start --block --address=$ip_head --redis-password=$redis_password & # Starting the workers
  sleep 5
done
