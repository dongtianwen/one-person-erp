// v1.11 数据标注与模型开发交付台账 API
import api from './index'

// ========== 数据集 ==========

export const getDatasets = (params) => api.get('/datasets', { params })
export const getDataset = (id) => api.get(`/datasets/${id}`)
export const createDataset = (data) => api.post('/datasets', data)
export const updateDataset = (id, data) => api.put(`/datasets/${id}`, data)
export const deleteDataset = (id) => api.delete(`/datasets/${id}`)

// 数据集版本
export const getDatasetVersions = (datasetId) => api.get(`/datasets/${datasetId}/versions`)
export const getDatasetVersion = (versionId) => api.get(`/datasets/versions/${versionId}`)
export const createDatasetVersion = (datasetId, data) => api.post(`/datasets/${datasetId}/versions`, data)
export const updateDatasetVersion = (versionId, data) => api.put(`/datasets/versions/${versionId}`, data)
export const deleteDatasetVersion = (versionId) => api.delete(`/datasets/versions/${versionId}`)
export const markVersionReady = (versionId) => api.patch(`/datasets/versions/${versionId}/ready`)
export const markVersionArchive = (versionId) => api.patch(`/datasets/versions/${versionId}/archive`)
export const getProjectDatasetSummary = (projectId) => api.get(`/datasets/projects/${projectId}/summary`)

// ========== 标注任务 ==========

export const getAnnotationTasks = (params) => api.get('/annotation-tasks', { params })
export const getAnnotationTask = (id) => api.get(`/annotation-tasks/${id}`)
export const createAnnotationTask = (data) => api.post('/annotation-tasks', data)
export const updateAnnotationTask = (id, data) => api.put(`/annotation-tasks/${id}`, data)
export const deleteAnnotationTask = (id) => api.delete(`/annotation-tasks/${id}`)
export const transitionAnnotationStatus = (id, data) => api.patch(`/annotation-tasks/${id}/status`, data)

// 标注规范
export const getAnnotationSpecs = (taskId) => api.get(`/annotation-tasks/${taskId}/specs`)
export const createAnnotationSpec = (taskId, data) => api.post(`/annotation-tasks/${taskId}/specs`, data)

// ========== 训练实验 ==========

export const getTrainingExperiments = (params) => api.get('/training-experiments', { params })
export const getTrainingExperiment = (id) => api.get(`/training-experiments/${id}`)
export const createTrainingExperiment = (data) => api.post('/training-experiments', data)
export const updateTrainingExperiment = (id, data) => api.put(`/training-experiments/${id}`, data)
export const deleteTrainingExperiment = (id) => api.delete(`/training-experiments/${id}`)

// 数据集版本关联
export const linkDatasetVersion = (expId, data) => api.post(`/training-experiments/${expId}/dataset-versions`, data)
export const unlinkDatasetVersion = (expId, versionId) => api.delete(`/training-experiments/${expId}/dataset-versions/${versionId}`)
export const getLinkedDatasetVersions = (expId) => api.get(`/training-experiments/${expId}/dataset-versions`)
export const getExperimentTraceability = (expId) => api.get(`/training-experiments/${expId}/traceability`)

// ========== 模型版本 ==========

export const getModelVersions = (params) => api.get('/model-versions', { params })
export const getModelVersion = (id) => api.get(`/model-versions/${id}`)
export const createModelVersion = (data) => api.post('/model-versions', data)
export const updateModelVersion = (id, data) => api.put(`/model-versions/${id}`, data)
export const deleteModelVersion = (id) => api.delete(`/model-versions/${id}`)
export const markModelReady = (id) => api.patch(`/model-versions/${id}/ready`)
export const markModelDeprecate = (id) => api.patch(`/model-versions/${id}/deprecate`)
export const getModelVersionTraceability = (id) => api.get(`/model-versions/${id}/traceability`)

// ========== 交付包 ==========

export const getDeliveryPackages = (params) => api.get('/delivery-packages', { params })
export const getDeliveryPackage = (id) => api.get(`/delivery-packages/${id}`)
export const createDeliveryPackage = (data) => api.post('/delivery-packages', data)
export const updateDeliveryPackage = (id, data) => api.put(`/delivery-packages/${id}`, data)
export const deleteDeliveryPackage = (id) => api.delete(`/delivery-packages/${id}`)

// 模型版本关联
export const linkPackageModelVersion = (pkgId, data) => api.post(`/delivery-packages/${pkgId}/model-versions`, data)
export const unlinkPackageModelVersion = (pkgId, mvId) => api.delete(`/delivery-packages/${pkgId}/model-versions/${mvId}`)

// 数据集版本关联
export const linkPackageDatasetVersion = (pkgId, data) => api.post(`/delivery-packages/${pkgId}/dataset-versions`, data)
export const unlinkPackageDatasetVersion = (pkgId, dvId) => api.delete(`/delivery-packages/${pkgId}/dataset-versions/${dvId}`)

// 交付与验收
export const markPackageReady = (pkgId) => api.patch(`/delivery-packages/${pkgId}/ready`)
export const deliverPackage = (pkgId) => api.patch(`/delivery-packages/${pkgId}/deliver`)
export const createPackageAcceptance = (pkgId, data) => api.post(`/delivery-packages/${pkgId}/acceptance`, data)
export const getPackageAcceptance = (pkgId) => api.get(`/delivery-packages/${pkgId}/acceptance`)
export const getPackageTraceability = (pkgId) => api.get(`/delivery-packages/${pkgId}/traceability`)
