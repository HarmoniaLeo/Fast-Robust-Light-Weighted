from turtle import screensize
import torch

from core.RED.ssd.utils.nms import batched_nms


class PostProcessor:
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.width = cfg.W
        self.height = cfg.H

    def __call__(self, detections):
        batches_scores, batches_boxes = detections
        device = batches_scores.device
        batch_size = batches_scores.size(0)
        results = []
        for batch_id in range(batch_size):
            scores, boxes = batches_scores[batch_id], batches_boxes[batch_id]  # (N, #CLS) (N, 4)
            # print("scores", scores[:5], scores.shape)
            # print("boxes", boxes[:5], boxes.shape)
            num_boxes = scores.shape[0]
            num_classes = scores.shape[1]

            boxes = boxes.view(num_boxes, 1, 4).expand(num_boxes, num_classes, 4)
            labels = torch.arange(num_classes, device=device)
            labels = labels.view(1, num_classes).expand_as(scores)
            # print("labels", labels[:5], labels.shape)
            # print("boxes", boxes[:5], boxes.shape)

            # remove predictions with the background label
            boxes = boxes[:, 1:]
            scores = scores[:, 1:]
            labels = labels[:, 1:]

            # batch everything, by making every class prediction be a separate instance
            boxes = boxes.reshape(-1, 4)
            scores = scores.reshape(-1)
            labels = labels.reshape(-1)

            # print("boxes", boxes[:5], boxes.shape)
            # print("labels", labels[:5], labels.shape)
            # print("boxes", boxes[:5], boxes.shape)
            # raise Exception("break")

            # remove low scoring boxes
            indices = torch.nonzero(scores > self.cfg.TEST.CONFIDENCE_THRESHOLD).squeeze(1)
            boxes, scores, labels = boxes[indices], scores[indices], labels[indices]

            boxes[:, 0::2] *= self.width
            boxes[:, 1::2] *= self.height

            keep = batched_nms(boxes, scores, labels, self.cfg.TEST.NMS_THRESHOLD)
            # keep only topk scoring predictions
            keep = keep[:15]
            boxes, scores, labels = boxes[keep], scores[keep], labels[keep] - 1
            results.append(torch.cat([boxes, scores[:,None], labels[:,None]],dim=1))

        return results
