import org.jenkinsci.plugins.pipeline.modeldefinition.Utils
@Library(['mlops-pipeline', 'common-utils']) _

ansiColor('xterm') {
    node('lmru-dockerhost') {
        try{
            String projectName = "test-project"
            String artServiceAccount = "lm-sa-mlops"
            String kfServiceAccount = "kubeflow-svc-mlops"
            setup(artServiceAccount)
            String branchTag
            List<String> tags
            String hash = env.GIT_COMMIT_HASH
            hash = hash[-4..-1]
            if (env.BRANCH_NAME == "master"){
                String imageTag = "master-${hash}".trim()
                branchTag = "master"
                tags = [branchTag, imageTag]
            } else {
                branchTag = env.BRANCH_NAME
                branchTag = branchTag.replaceAll('_', '-')
                tags = [branchTag]
            }
            stage("Build and push base"){
                dockerUtils.buildImage([
                    projectName: projectName,
                    artifactoryImageName: "base-image",
                    imageTags: tags,
                    pathToDockerfile: "./docker/base_image/Dockerfile",
                ])
            }
            stage("Build and push KF pipeline") {
                kubeflowUtils.uploadPipeline([
                        serviceAccount:kfServiceAccount,
                        pathToDockerfile:'docker/kubeflow_pipeline/Dockerfile',
                        pipelinePath:'pipeline.yaml',
                        pipelineName:'train',
                        namespace:'main',
                    ])
            }
        } catch (err) {
            println err
        }
    }
}

void setup(String serviceAccount) {
    stage("Setup") {
        cleanWs()
        checkout scm
        prepareParameters(serviceAccount)
    }
}

void prepareParameters(String serviceAccount) {

    env.SERVICE_ACCOUNT = "${serviceAccount}"
    env.GIT_REPO = scm.userRemoteConfigs[0].url
    env.GIT_COMMIT_HASH = getCommitSha()
}

def getCommitSha() {
  return sh(returnStdout: true, script: 'git rev-parse HEAD')
}