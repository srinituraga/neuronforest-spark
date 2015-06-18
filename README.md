neuronforest-spark
==================

**Contents**

* Importing the Project
* Generating and Running on Training Data
* Setup up on Janelia Cluster
* Running on Janelia Cluster
* Setup on EC2

**Importing the Project**

Clone the repo into a local directory.

Download Intellij and the scala plugin for Intellij.

Inside of Intellij (or Eclipse), go to File -> New -> Project... and on the left-hand side select Scala and click next.

In the Project Location dialog, navigate to the directory where the repo is cloned. 
Now, select Java sdk 1.7 (1.8 is not yet stable with the Intellij scala plugin), and select scala-sdk-2.10 (2.11 has problems with this project.)  

Next, in the project explorer on the left, right click on each of the jars in the lib folder and select "Add as library".  Now you should be able to compile the project.  In order to run it, set up the run configurations to call Main.scala.  

***Note: if your files are missing dependencies on spark, then you can fix this by downloading a jar file from the apache spark website and adding it as a library***

**Generating and Running on Training Data**

In order to generate the training data, Helmstaedter.mat is required in the neuronforest-spark directory.  Then run make_training_data.py.  This results in a folder called data being created.  Now the program can be run from within Intellij, and the output will be saved in a folder called "mnt".  

**Setup on Janelia Cluster**

In order to setup on the Janelia cluster, the project must be made into a jar file and moved onto the cluster.  This is done by clicking File -> Project Structure -> Artifacts and creating a new Jar.  Use the given manifest file to set up its classpath.  Make sure you drag the project compile output from the right folder into the jar.  You must also include the scala sdk unless you have it installed to your command line.  Intellij has problems when the jar is built too many folders down, so build the jar to out/artifacts/main.jar.  Finally, the jar can be made to build every time you make the project. 

On the local machine, the data folder should be placed in the artifacts folder.  On the cluster, the data folder should be placed at the root directory.  In addition, the jars in the lib folder and the scripts in the scripts folder should be placed in the same folder as main.jar.

**Running on Janelia Cluster**

In order to run, we use scripts from https://github.com/saalfeldlab/java-spark-workshop.  In order to run the scripts we use the following command:

```
/path/to/inflame.sh <N_NODES> /path/to/main.jar Main <ARGV>
```
In order to view the logs,  use the following 2 commands:
```
qstat
sed -r 's/^M/\n/g' ~/.sparklogs/qsub-argument-wrap-script.sh.o<job-id> | less
```
**Setup on EC2:**

./spark-ec2 -k luke -i ~/luke.pem -s 36 --instance-type=r3.xlarge --master-instance-type=r3.4xlarge --region=eu-west-1 --spark-version=e895e0cbecbbec1b412ff21321e57826d2d0a982 launch *NAME*

MASTER=`spark-ec2 -k luke -i ~/luke.pem --region=eu-west-1 get-master *NAME* | tail -1`

(echo $MASTER && ssh -n -i ~/luke.pem root@$MASTER 'cat /root/spark-ec2/slaves') | (tasks=""; for v in ${volumes[0]} ${volumes[@]}; do
	read line; ssh -n -o StrictHostKeyChecking=no -i ~/luke.pem -t -t root@$line 'curl "https://s3.amazonaws.com/aws-cli/awscli-bundle.zip" -o "awscli-bundle.zip" && unzip awscli-bundle.zip && sudo ./awscli-bundle/install -i /usr/local/aws -b /usr/local/bin/aws' &
tasks="$tasks $!"; done; for t in $tasks; do wait $t; done)

./spark-ec2 -k luke -i ~/luke.pem --region=eu-west-1 login *NAME*

*export aws credentials*

spark-ec2/copy-dir aws-credentials
